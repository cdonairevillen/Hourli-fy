"""Usuarios fantasma: personas con horas importadas que aún no tienen cuenta.

Un fantasma es un `User` normal con `is_ghost = True`, sin contraseña ni Google y con un email
inventado (`.invalid`), así que nadie puede entrar con él. Es miembro del espacio como cualquiera,
así que sus horas salen en los informes con su nombre.

Para reclamarlo, el dueño (o un admin) genera un link: es una invitación normal con
`claim_user_id`. Quien la acepta se queda las horas, los espacios y los accesos del fantasma, y el
fantasma queda cerrado (`deleted_at`).
"""

import uuid
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.security import hash_invitation_token, new_invitation_token
from app.models import Invitation, Membership, Project, ProjectMember, TimeEntry, User, Workspace
from app.models.common import utc_now
from app.services.access import grant_project, revoke_projects
from app.services.workspaces import INVITATION_DAYS


def create_ghost(session: Session, workspace_id: uuid.UUID, name: str) -> User:
    """Crea el fantasma y lo hace miembro limitado del espacio (sin proyectos aún).

    Limitado y no "todos los proyectos": al reclamarlo, la persona solo recibe acceso a los
    proyectos donde el fantasma tenía horas. Hace falta commit después.
    """
    ghost_id = uuid.uuid4()
    ghost = User(
        id=ghost_id,
        name=name,
        email=f"fantasma-{ghost_id}@hourlify.invalid",
        is_ghost=True,
    )
    session.add(ghost)
    session.flush()
    session.add(Membership(workspace_id=workspace_id, user_id=ghost.id, all_projects=False))
    session.flush()
    return ghost


def is_claimable(ghost: User | None) -> bool:
    return ghost is not None and ghost.is_ghost and ghost.deleted_at is None


def create_claim_invitation(
    session: Session, workspace: Workspace, ghost: User, created_by: uuid.UUID
) -> tuple[Invitation, str]:
    """Link de un solo uso (caduca como las invitaciones) para reclamar al fantasma.

    Devuelve la invitación y el token (que solo existe ahora: en la BD queda su hash).
    """
    if workspace.archived:
        raise HTTPException(status.HTTP_409_CONFLICT, "El espacio está archivado")
    if not is_claimable(ghost):
        raise HTTPException(status.HTTP_409_CONFLICT, "Solo se reclaman usuarios fantasma")
    token = new_invitation_token()
    invitation = Invitation(
        workspace_id=workspace.id,
        token_hash=hash_invitation_token(token),
        created_by=created_by,
        expires_at=utc_now() + timedelta(days=INVITATION_DAYS),
        max_uses=1,
        claim_user_id=ghost.id,
    )
    session.add(invitation)
    session.commit()
    session.refresh(invitation)
    return invitation, token


def claim_ghost(session: Session, ghost: User, user: User) -> None:
    """Pasa todo lo del fantasma a `user`: registros, pertenencias y accesos a proyectos.

    Si alguna hora del fantasma se solapa con las de `user`, no se mueve nada (409): la
    restricción de solapes de la BD lo impide y así no queda a medias. Hace falta commit después.
    """
    if not is_claimable(ghost):
        raise HTTPException(status.HTTP_410_GONE, "Estas horas ya se han reclamado")
    if user.is_ghost or user.id == ghost.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "No puedes reclamar estas horas")

    # Un solo UPDATE: si algo se solapa, Postgres lo rechaza entero.
    try:
        with session.begin_nested():
            session.exec(
                update(TimeEntry).where(TimeEntry.user_id == ghost.id).values(user_id=user.id)
            )
    except IntegrityError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Algunas de estas horas se solapan con las tuyas: corrígelas antes de reclamarlas",
        ) from error

    now = utc_now()
    ghost_memberships = session.exec(
        select(Membership).where(Membership.user_id == ghost.id, Membership.removed_at.is_(None))
    ).all()
    for ghost_membership in ghost_memberships:
        workspace_id = ghost_membership.workspace_id
        granted = session.exec(
            select(ProjectMember.project_id)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(
                Project.workspace_id == workspace_id,
                ProjectMember.user_id == ghost.id,
                ProjectMember.removed_at.is_(None),
            )
        ).all()
        membership = session.get(Membership, (workspace_id, user.id))
        if membership is None:
            membership = Membership(
                workspace_id=workspace_id,
                user_id=user.id,
                all_projects=ghost_membership.all_projects,
            )
        elif membership.removed_at is not None:
            # Volvía a un espacio del que salió: entra con lo que tenía el fantasma.
            membership.removed_at = None
            membership.joined_at = now
            membership.all_projects = ghost_membership.all_projects
        else:
            membership.all_projects = membership.all_projects or ghost_membership.all_projects
        session.add(membership)
        if not membership.all_projects:
            for project_id in granted:
                grant_project(session, project_id, user.id)
        ghost_membership.removed_at = now
        session.add(ghost_membership)
        revoke_projects(session, workspace_id, ghost.id)

    ghost.deleted_at = now
    session.add(ghost)


def ghost_workspace(session: Session, ghost: User) -> Workspace | None:
    """El espacio del fantasma (lo crea el importador de un espacio: tiene uno)."""
    return session.exec(
        select(Workspace)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == ghost.id, Membership.removed_at.is_(None))
        .order_by(Membership.joined_at)
    ).first()
