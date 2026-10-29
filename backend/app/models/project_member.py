import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.common import TZDateTime, utc_now


class ProjectMember(SQLModel, table=True):
    """Acceso a un proyecto concreto de un miembro limitado (membership.all_projects = False)."""

    __tablename__ = "project_members"

    project_id: uuid.UUID = Field(foreign_key="projects.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True, index=True)
    added_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    # null = acceso activo. Al quitárselo se rellena (no se borra: igual que las membresías).
    removed_at: datetime | None = Field(default=None, sa_type=TZDateTime)
