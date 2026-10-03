import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.common import TZDateTime, utc_now


class Invitation(SQLModel, table=True):
    """Link de invitación a un espacio. Solo se guarda el hash del token, nunca el token."""

    __tablename__ = "invitations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    token_hash: str = Field(unique=True)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    expires_at: datetime = Field(sa_type=TZDateTime)
    # null = usos ilimitados mientras no caduque.
    max_uses: int | None = None
    uses: int = 0
    revoked_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
