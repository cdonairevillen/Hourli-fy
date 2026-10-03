import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.common import TZDateTime, utc_now


class User(SQLModel, table=True):
    """Persona que entra con Google. Se crea sola en su primer login."""

    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # "sub" del ID token: el identificador estable de la cuenta de Google (el email puede cambiar).
    google_sub: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    name: str
    avatar_url: str | None = None
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
