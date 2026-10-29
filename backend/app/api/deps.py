"""Dependencias compartidas por las rutas: sesión de BD, usuario actual y acceso a un espacio."""

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import SESSION_COOKIE, read_session_token
from app.db import get_session
from app.models import Membership, User, Workspace

SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(
    session: SessionDep,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    """Usuario de la cookie de sesión; 401 si no hay sesión válida."""
    # No se llama `token`: chocaría con el parámetro de ruta de /invitations/{token}.
    user_id = read_session_token(session_token) if session_token else None
    user = session.get(User, user_id) if user_id else None
    # Una cookie aún válida de una cuenta ya eliminada tampoco sirve.
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No has iniciado sesión")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def is_admin(user: User) -> bool:
    """Su email está en ADMIN_EMAILS (.env): puede entrar al panel /admin."""
    admins = {email.strip().lower() for email in settings.admin_emails}
    return user.deleted_at is None and user.email.lower() in admins


@dataclass
class WorkspaceAccess:
    """El espacio de la ruta y la relación del usuario actual con él."""

    workspace: Workspace
    membership: Membership
    user: User

    @property
    def is_owner(self) -> bool:
        return self.workspace.owner_id == self.user.id


def get_workspace_access(wid: uuid.UUID, session: SessionDep, user: CurrentUser) -> WorkspaceAccess:
    """Comprueba que el usuario es miembro activo del espacio `wid`.

    Devuelve 404 (y no 403) si no lo es: así no se revela si el espacio existe.
    """
    membership = session.exec(
        select(Membership).where(
            Membership.workspace_id == wid,
            Membership.user_id == user.id,
            Membership.removed_at.is_(None),
        )
    ).first()
    workspace = session.get(Workspace, wid) if membership else None
    if membership is None or workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Espacio no encontrado")
    return WorkspaceAccess(workspace=workspace, membership=membership, user=user)


MemberAccess = Annotated[WorkspaceAccess, Depends(get_workspace_access)]


def get_owner_access(access: MemberAccess) -> WorkspaceAccess:
    """Como get_workspace_access, pero además exige ser el dueño (403 si no)."""
    if not access.is_owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el dueño del espacio puede hacer esto")
    return access


OwnerAccess = Annotated[WorkspaceAccess, Depends(get_owner_access)]
