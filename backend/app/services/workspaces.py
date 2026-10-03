"""Reglas de espacios e invitaciones que usan varias rutas."""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.models import Invitation, User, Workspace
from app.models.common import utc_now
from app.schemas import InvitationRead, InvitationStatus, WorkspaceRead

MAX_OWNED_WORKSPACES = 5
INVITATION_DAYS = 10


def ensure_can_own_another(session: Session, user_id: uuid.UUID) -> None:
    """409 si el usuario ya es dueño de MAX_OWNED_WORKSPACES espacios sin archivar.

    Bloquea la fila del usuario (SELECT ... FOR UPDATE) hasta el commit: así dos peticiones
    simultáneas no pueden contar 4 a la vez y crear el 5.º y el 6.º.
    """
    session.exec(select(User).where(User.id == user_id).with_for_update()).one()
    owned = session.exec(
        select(func.count())
        .select_from(Workspace)
        .where(Workspace.owner_id == user_id, Workspace.archived.is_(False))
    ).one()
    if owned >= MAX_OWNED_WORKSPACES:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Límite alcanzado: como máximo {MAX_OWNED_WORKSPACES} espacios propios sin archivar",
        )


def workspace_read(workspace: Workspace, user_id: uuid.UUID) -> WorkspaceRead:
    return WorkspaceRead(
        id=workspace.id,
        name=workspace.name,
        owner_id=workspace.owner_id,
        archived=workspace.archived,
        is_owner=workspace.owner_id == user_id,
        created_at=workspace.created_at,
    )


def invitation_status(invitation: Invitation, workspace: Workspace) -> InvitationStatus:
    """Estado de un link: solo "active" permite unirse."""
    if workspace.archived:
        return "archived"
    if invitation.revoked_at is not None:
        return "revoked"
    if invitation.expires_at <= utc_now():
        return "expired"
    if invitation.max_uses is not None and invitation.uses >= invitation.max_uses:
        return "exhausted"
    return "active"


def invitation_read(invitation: Invitation, workspace: Workspace) -> InvitationRead:
    return InvitationRead(
        id=invitation.id,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        max_uses=invitation.max_uses,
        uses=invitation.uses,
        status=invitation_status(invitation, workspace),
    )
