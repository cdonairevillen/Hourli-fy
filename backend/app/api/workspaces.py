import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import CurrentUser, MemberAccess, OwnerAccess, SessionDep
from app.core.security import hash_invitation_token, new_invitation_token
from app.models import Invitation, Membership, User, Workspace
from app.models.common import utc_now
from app.schemas import (
    InvitationCreate,
    InvitationCreated,
    InvitationRead,
    MemberRead,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
)
from app.services.workspaces import (
    INVITATION_DAYS,
    ensure_can_own_another,
    invitation_read,
    workspace_read,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("")
def list_my_workspaces(session: SessionDep, user: CurrentUser) -> list[WorkspaceRead]:
    """Espacios en los que soy miembro activo (propios e invitados, archivados incluidos)."""
    workspaces = session.exec(
        select(Workspace)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == user.id, Membership.removed_at.is_(None))
        .order_by(Workspace.created_at)
    ).all()
    return [workspace_read(workspace, user.id) for workspace in workspaces]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_workspace(
    body: WorkspaceCreate, session: SessionDep, user: CurrentUser
) -> WorkspaceRead:
    """Crea un espacio del que soy dueño (y miembro). Máximo 5 propios sin archivar."""
    ensure_can_own_another(session, user.id)
    workspace = Workspace(name=body.name.strip(), owner_id=user.id)
    session.add(workspace)
    session.flush()
    session.add(Membership(workspace_id=workspace.id, user_id=user.id))
    session.commit()
    session.refresh(workspace)
    return workspace_read(workspace, user.id)


@router.patch("/{wid}")
def update_workspace(
    body: WorkspaceUpdate, session: SessionDep, access: OwnerAccess
) -> WorkspaceRead:
    """Renombrar, archivar/desarchivar o transferir la propiedad a otro miembro activo."""
    workspace = access.workspace
    new_owner_id = body.owner_id if body.owner_id is not None else workspace.owner_id
    archived = body.archived if body.archived is not None else workspace.archived

    if new_owner_id != workspace.owner_id:
        is_member = session.exec(
            select(Membership).where(
                Membership.workspace_id == workspace.id,
                Membership.user_id == new_owner_id,
                Membership.removed_at.is_(None),
            )
        ).first()
        if is_member is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "El nuevo dueño debe ser miembro del espacio"
            )
    # Pasa a contar en el límite de alguien si queda activo y cambia de dueño o se desarchiva.
    if not archived and (new_owner_id != workspace.owner_id or workspace.archived):
        ensure_can_own_another(session, new_owner_id)

    if body.name is not None:
        workspace.name = body.name.strip()
    workspace.archived = archived
    workspace.owner_id = new_owner_id
    session.add(workspace)
    session.commit()
    session.refresh(workspace)
    return workspace_read(workspace, access.user.id)


@router.get("/{wid}/members")
def list_members(session: SessionDep, access: MemberAccess) -> list[MemberRead]:
    """Miembros activos del espacio, el dueño primero."""
    rows = session.exec(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.workspace_id == access.workspace.id, Membership.removed_at.is_(None))
        .order_by(Membership.joined_at)
    ).all()
    members = [
        MemberRead(
            user_id=user.id,
            name=user.name,
            email=user.email,
            avatar_url=user.avatar_url,
            is_owner=user.id == access.workspace.owner_id,
            joined_at=membership.joined_at,
        )
        for membership, user in rows
    ]
    return sorted(members, key=lambda member: not member.is_owner)


@router.delete("/{wid}/members/{uid}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(uid: uuid.UUID, session: SessionDep, access: MemberAccess) -> None:
    """Salir del espacio (uid = yo) o expulsar a alguien (solo el dueño).

    No se borra la fila: se marca `removed_at` para que sus horas sigan en los informes.
    """
    is_self = uid == access.user.id
    if not is_self and not access.is_owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el dueño puede expulsar miembros")
    if uid == access.workspace.owner_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El dueño no puede salir: transfiere antes el espacio o archívalo",
        )
    membership = (
        access.membership
        if is_self
        else session.exec(
            select(Membership).where(
                Membership.workspace_id == access.workspace.id,
                Membership.user_id == uid,
                Membership.removed_at.is_(None),
            )
        ).first()
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Miembro no encontrado")
    membership.removed_at = utc_now()
    session.add(membership)
    session.commit()


@router.get("/{wid}/invitations")
def list_invitations(session: SessionDep, access: OwnerAccess) -> list[InvitationRead]:
    """Links del espacio, los más recientes primero (también caducados y revocados)."""
    invitations = session.exec(
        select(Invitation)
        .where(Invitation.workspace_id == access.workspace.id)
        .order_by(Invitation.created_at.desc())
    ).all()
    return [invitation_read(invitation, access.workspace) for invitation in invitations]


@router.post("/{wid}/invitations", status_code=status.HTTP_201_CREATED)
def create_invitation(
    body: InvitationCreate, session: SessionDep, access: OwnerAccess
) -> InvitationCreated:
    """Crea un link que caduca a los 10 días. El token solo se ve en esta respuesta."""
    if access.workspace.archived:
        raise HTTPException(status.HTTP_409_CONFLICT, "El espacio está archivado")
    token = new_invitation_token()
    invitation = Invitation(
        workspace_id=access.workspace.id,
        token_hash=hash_invitation_token(token),
        created_by=access.user.id,
        expires_at=utc_now() + timedelta(days=INVITATION_DAYS),
        max_uses=body.max_uses,
    )
    session.add(invitation)
    session.commit()
    session.refresh(invitation)
    read = invitation_read(invitation, access.workspace)
    return InvitationCreated(**read.model_dump(), token=token)


@router.delete("/{wid}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(invitation_id: uuid.UUID, session: SessionDep, access: OwnerAccess) -> None:
    """Revoca un link: deja de servir aunque no haya caducado."""
    invitation = session.get(Invitation, invitation_id)
    if invitation is None or invitation.workspace_id != access.workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitación no encontrada")
    if invitation.revoked_at is None:
        invitation.revoked_at = utc_now()
        session.add(invitation)
        session.commit()
