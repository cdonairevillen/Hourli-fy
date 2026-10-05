"""Cuerpos de petición y respuesta de la API (lo que entra y sale en JSON)."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


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


# --- Catálogo: proyectos, tipologías ("labels") y subtipologías ("sublabels") ---

CatalogName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
# Color en hex: el front ofrece una paleta, pero la API acepta cualquier #RRGGBB.
HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
DEFAULT_PROJECT_COLOR = "#3b82f6"


class ProjectCreate(BaseModel):
    name: CatalogName
    color: HexColor = DEFAULT_PROJECT_COLOR


class ProjectUpdate(BaseModel):
    """Solo se cambia lo que llega."""

    name: CatalogName | None = None
    color: HexColor | None = None
    archived: bool | None = None


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    color: str
    archived: bool
    created_at: datetime


class CatalogItemCreate(BaseModel):
    """Crear una tipología o una subtipología: solo lleva nombre."""

    name: CatalogName


class CatalogItemUpdate(BaseModel):
    name: CatalogName | None = None
    archived: bool | None = None


class SubcategoryRead(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    archived: bool


class CategoryRead(BaseModel):
    id: uuid.UUID
    name: str
    archived: bool
    subcategories: list[SubcategoryRead]
