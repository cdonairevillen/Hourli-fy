"""Sesión (JWT en cookie) y tokens de invitación."""

import hashlib
import secrets
import uuid
from datetime import timedelta

import jwt

from app.core.config import settings
from app.models.common import utc_now

SESSION_COOKIE = "session"
JWT_ALGORITHM = "HS256"


def create_session_token(user_id: uuid.UUID) -> str:
    """JWT firmado con SECRET_KEY que identifica al usuario durante `session_days`."""
    expires = utc_now() + timedelta(days=settings.session_days)
    return jwt.encode({"sub": str(user_id), "exp": expires}, settings.secret_key, JWT_ALGORITHM)


def read_session_token(token: str) -> uuid.UUID | None:
    """Devuelve el id de usuario del JWT, o None si es inválido o ha caducado."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def new_invitation_token() -> str:
    """Token aleatorio de 256 bits para el link de invitación."""
    return secrets.token_urlsafe(32)


def hash_invitation_token(token: str) -> str:
    """SHA-256 del token. Basta (no hace falta argon2) porque el token es aleatorio y largo:
    no se puede adivinar por fuerza bruta como una contraseña."""
    return hashlib.sha256(token.encode()).hexdigest()
