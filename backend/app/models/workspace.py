import uuid
from datetime import datetime

from sqlalchemy import true
from sqlmodel import Field, SQLModel

from app.models.common import TZDateTime, utc_now


class Workspace(SQLModel, table=True):
    """Espacio aislado (un estudio, una empresa, un equipo). Su dueño es quien lo crea."""

    __tablename__ = "workspaces"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    owner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    archived: bool = False
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)


class Membership(SQLModel, table=True):
    """Pertenencia de un usuario a un espacio. El dueño también tiene la suya."""

    __tablename__ = "memberships"

    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True, index=True)
    joined_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    # null = miembro activo. Al expulsar o salir se rellena (no se borra: sus horas cuentan).
    removed_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    # True = ve todos los proyectos del espacio, también los que se creen después (invitación al
    # espacio, y siempre el dueño). False = solo los de project_members (invitación a un proyecto).
    all_projects: bool = Field(default=True, sa_column_kwargs={"server_default": true()})
