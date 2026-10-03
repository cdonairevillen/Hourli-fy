"""Cuerpos de petición y respuesta de la API (lo que entra y sale en JSON)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GoogleLogin(BaseModel):
    credential: str


class UserRead(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    avatar_url: str | None


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class WorkspaceUpdate(BaseModel):
    """Todos los campos son opcionales: solo se cambia lo que llega."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    archived: bool | None = None
    # Transferir la propiedad a otro miembro activo.
    owner_id: uuid.UUID | None = None


class WorkspaceRead(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    archived: bool
    is_owner: bool
    created_at: datetime


class MemberRead(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    avatar_url: str | None
    is_owner: bool
    joined_at: datetime


class InvitationCreate(BaseModel):
    # null = sin límite de usos (solo caduca por fecha).
    max_uses: int | None = Field(default=None, ge=1, le=100)


InvitationStatus = Literal["active", "expired", "revoked", "exhausted", "archived"]


class InvitationRead(BaseModel):
    id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    max_uses: int | None
    uses: int
    status: InvitationStatus


class InvitationCreated(InvitationRead):
    # El token solo se devuelve al crear: en la BD únicamente queda su hash.
    token: str


class InvitationPreview(BaseModel):
    """Lo que ve quien abre un link, aunque no haya iniciado sesión."""

    workspace_name: str
    owner_name: str
    expires_at: datetime
    status: InvitationStatus
