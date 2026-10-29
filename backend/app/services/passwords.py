"""Cuentas con email y contraseña: registro, login, recuperar y cambiar la contraseña."""

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.passwords import hash_password, verify_password
from app.core.security import hash_invitation_token, new_invitation_token
from app.models import PasswordResetToken, User
from app.models.common import utc_now
from app.services.email import EmailMessage, EmailSender, send_safely

RESET_TOKEN_LIFETIME = timedelta(hours=1)
WRONG_CREDENTIALS = "Email o contraseña incorrectos"


def normalize_email(email: str) -> str:
    """ "Ana@Hotmail.com " y "ana@hotmail.com" son la misma cuenta."""
    return email.strip().lower()


def find_active_user_by_email(session: Session, email: str) -> User | None:
    user = session.exec(select(User).where(User.email == normalize_email(email))).first()
    return user if user is not None and user.deleted_at is None else None


def register_user(session: Session, name: str, email: str, password: str) -> User:
    """Crea una cuenta con contraseña. 409 si el email ya tiene cuenta (de Google o no)."""
    email = normalize_email(email)
    taken = "Ya hay una cuenta con ese email: entra, o recupera la contraseña si no la recuerdas"
    if session.exec(select(User).where(User.email == email)).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, taken)
    user = User(email=email, name=name, password_hash=hash_password(password))
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:
        # Dos registros a la vez con el mismo email: la restricción única decide.
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, taken) from error
    session.refresh(user)
    return user


def authenticate(session: Session, email: str, password: str) -> User:
    """El usuario si email y contraseña coinciden; si no, 401 sin decir cuál de los dos falló."""
    user = find_active_user_by_email(session, email)
    # Se verifica siempre (contra un hash ficticio si no hay usuario) para tardar lo mismo.
    matches = verify_password(password, user.password_hash if user else None)
    if user is None or not matches:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, WRONG_CREDENTIALS)
    return user


def request_password_reset(session: Session, email: str, send: EmailSender) -> None:
    """Si el email tiene cuenta, le manda un link de un solo uso que caduca en 1 hora.

    Si no la tiene, no hace nada: la ruta responde igual en los dos casos.
    """
    user = find_active_user_by_email(session, email)
    if user is None:
        return
    token = new_invitation_token()
    session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_invitation_token(token),
            expires_at=utc_now() + RESET_TOKEN_LIFETIME,
        )
    )
    session.commit()
    link = f"{settings.frontend_url.rstrip('/')}/recuperar/{token}"
    send_safely(
        send,
        EmailMessage(
            to=user.email,
            subject="Recupera tu contraseña de Hourli-fy",
            text=(
                f"Hola, {user.name}:\n\n"
                f"Para elegir una contraseña nueva, abre este link (caduca en 1 hora y solo "
                f"sirve una vez):\n\n{link}\n\n"
                f"Si no lo has pedido tú, ignora este email: tu contraseña no cambia."
            ),
        ),
    )


def invalidate_reset_tokens(session: Session, user: User) -> None:
    """Gasta los links de recuperación pendientes del usuario."""
    pending = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)
        )
    ).all()
    for reset in pending:
        reset.used_at = utc_now()
        session.add(reset)


def reset_password(session: Session, token: str, password: str) -> User:
    """Cambia la contraseña con un link válido y lo gasta (a él y a los demás pendientes)."""
    reset = session.exec(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_invitation_token(token))
        .with_for_update()
    ).first()
    user = session.get(User, reset.user_id) if reset is not None else None
    if (
        reset is None
        or user is None
        or reset.used_at is not None
        or reset.expires_at <= utc_now()
        or user.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_410_GONE, "El link ha caducado o ya se usó: pide uno nuevo")
    user.password_hash = hash_password(password)
    session.add(user)
    invalidate_reset_tokens(session, user)
    session.commit()
    session.refresh(user)
    return user


def change_password(
    session: Session, user: User, current_password: str | None, new_password: str
) -> None:
    """Cambiar la contraseña (pide la actual) o ponerla por primera vez (cuenta de Google)."""
    if user.password_hash is not None and not verify_password(
        current_password or "", user.password_hash
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña actual no es correcta")
    user.password_hash = hash_password(new_password)
    session.add(user)
    invalidate_reset_tokens(session, user)
    session.commit()
