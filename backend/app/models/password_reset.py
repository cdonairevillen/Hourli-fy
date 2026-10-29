import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.common import TZDateTime, utc_now


class PasswordResetToken(SQLModel, table=True):
    """Link de "recuperar contraseña". Como en las invitaciones, solo se guarda su hash."""

    __tablename__ = "password_reset_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True)
    expires_at: datetime = Field(sa_type=TZDateTime)
    # Se rellena al usarlo: cada link sirve una sola vez.
    used_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
