import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.common import TZDateTime, utc_now


class User(SQLModel, table=True):
    """Persona con cuenta: se registra con email y contraseña o entra con Google (o ambas)."""

    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # "sub" del ID token: el identificador estable de la cuenta de Google (el email puede cambiar).
    # null = cuenta solo con contraseña.
    google_sub: str | None = Field(default=None, unique=True, index=True)
    # Siempre en minúsculas: "Ana@Hotmail.com" y "ana@hotmail.com" son la misma cuenta.
    email: str = Field(unique=True, index=True)
    name: str
    avatar_url: str | None = None
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    # Cuenta eliminada: sus datos personales se anonimizan, pero la fila (y sus horas) se queda.
    deleted_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    # Hash argon2 de la contraseña (nunca la contraseña). null = cuenta solo de Google.
    password_hash: str | None = None
