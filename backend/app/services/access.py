"""Acceso a proyectos dentro de un espacio.

Un miembro ve todos los proyectos del espacio (`membership.all_projects`, lo normal y siempre en
el dueño) o solo los que tiene en `project_members` (entró con una invitación a un proyecto).
"""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Membership, Project, ProjectMember, Workspace
from app.models.common import utc_now


def has_all_projects(workspace: Workspace, membership: Membership) -> bool:
    return workspace.owner_id == membership.user_id or membership.all_projects


def granted_project_ids(session: Session, workspace_id: uuid.UUID, user_id: uuid.UUID) -> set:
    """Proyectos del espacio con acceso activo en project_members para ese usuario."""
    return set(
        session.exec(
            select(ProjectMember.project_id)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(
                Project.workspace_id == workspace_id,
                ProjectMember.user_id == user_id,
                ProjectMember.removed_at.is_(None),
            )
        ).all()
    )


def accessible_project_ids(
    session: Session, workspace: Workspace, membership: Membership
) -> set | None:
    """Ids de los proyectos que puede ver; None = todos (presentes y futuros)."""
    if has_all_projects(workspace, membership):
        return None
    return granted_project_ids(session, workspace.id, membership.user_id)


def can_access_project(
    session: Session, workspace: Workspace, membership: Membership, project_id: uuid.UUID
) -> bool:
    allowed = accessible_project_ids(session, workspace, membership)
    return allowed is None or project_id in allowed


def ensure_project_access(
    session: Session, workspace: Workspace, membership: Membership, project_id: uuid.UUID
) -> None:
    """404 (como un proyecto que no existe) si el miembro no tiene acceso a ese proyecto."""
    if not can_access_project(session, workspace, membership, project_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")


def grant_project(session: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Da (o devuelve) el acceso a un proyecto. Hace falta commit después."""
    row = session.get(ProjectMember, (project_id, user_id))
    if row is None:
        session.add(ProjectMember(project_id=project_id, user_id=user_id))
    elif row.removed_at is not None:
        row.removed_at = None
        row.added_at = utc_now()
        session.add(row)


def revoke_projects(
    session: Session, workspace_id: uuid.UUID, user_id: uuid.UUID, keep: set | None = None
) -> None:
    """Quita los accesos a proyectos del espacio, salvo los de `keep`. Hace falta commit después."""
    rows = session.exec(
        select(ProjectMember)
        .join(Project, Project.id == ProjectMember.project_id)
        .where(
            Project.workspace_id == workspace_id,
            ProjectMember.user_id == user_id,
            ProjectMember.removed_at.is_(None),
        )
    ).all()
    for row in rows:
        if keep is None or row.project_id not in keep:
            row.removed_at = utc_now()
            session.add(row)
