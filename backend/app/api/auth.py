from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, is_admin
from app.core.config import settings
from app.core.google import GoogleIdentity, GoogleLoginError, get_google_verifier
from app.core.security import SESSION_COOKIE, create_session_token
from app.models import User
from app.schemas import (
    ChangePasswordBody,
    ForgotPasswordBody,
    GoogleLogin,
    LoginBody,
    RegisterBody,
    ResetPasswordBody,
    UserRead,
)
from app.services.account import delete_account
from app.services.email import EmailSender, get_email_sender
from app.services.passwords import (
    authenticate,
    change_password,
    invalidate_reset_tokens,
    normalize_email,
    register_user,
    request_password_reset,
    reset_password,
)
from app.services.rate_limit import LOGIN_LIMIT, RESET_LIMIT

router = APIRouter(prefix="/auth", tags=["auth"])

GoogleVerifier = Annotated[Callable[[str], GoogleIdentity], Depends(get_google_verifier)]
EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]


def user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        name=user.name,
        email=user.email,
        avatar_url=user.avatar_url,
        has_password=user.password_hash is not None,
        is_admin=is_admin(user),
    )


def set_session_cookie(response: Response, user: User) -> None:
    """La cookie de sesión (JWT propio, httpOnly), igual entre por donde entre."""
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user.id),
        max_age=settings.session_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"


# --- Email y contraseña ---


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterBody, response: Response, session: SessionDep) -> UserRead:
    """Crea una cuenta con cualquier email (sin confirmación) y deja la sesión abierta."""
    user = register_user(session, body.name, body.email, body.password)
    set_session_cookie(response, user)
    return user_read(user)


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response, session: SessionDep) -> UserRead:
    """Entrar con email y contraseña. Máximo 10 intentos cada 15 min por IP y email."""
    LOGIN_LIMIT.hit(f"{client_ip(request)}|{normalize_email(body.email)}")
    user = authenticate(session, body.email, body.password)
    set_session_cookie(response, user)
    return user_read(user)


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(body: ForgotPasswordBody, session: SessionDep, send: EmailSenderDep) -> dict:
    """Manda un link para elegir contraseña nueva. Responde lo mismo exista o no la cuenta."""
    RESET_LIMIT.hit(normalize_email(body.email))
    request_password_reset(session, body.email, send)
    return {"detail": "Si el email tiene cuenta, te hemos enviado un link para recuperarla"}


@router.post("/password/reset")
def reset_with_token(body: ResetPasswordBody, response: Response, session: SessionDep) -> UserRead:
    """Contraseña nueva con el link del email; además abre la sesión."""
    user = reset_password(session, body.token, body.password)
    set_session_cookie(response, user)
    return user_read(user)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def set_password(body: ChangePasswordBody, session: SessionDep, user: CurrentUser) -> None:
    """Cambiar mi contraseña, o ponerme una si mi cuenta es solo de Google."""
    change_password(session, user, body.current_password, body.new_password)


# --- Google ---


@router.post("/google")
def login_with_google(
    body: GoogleLogin, response: Response, session: SessionDep, verify: GoogleVerifier
) -> UserRead:
    """Recibe el ID token de Google, crea o une la cuenta y pone la cookie."""
    if not settings.google_client_id:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Falta GOOGLE_CLIENT_ID")
    try:
        identity = verify(body.credential)
    except GoogleLoginError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de Google no válido") from error
    if not identity.email_verified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "El email de Google no está verificado")
    email = normalize_email(identity.email)

    user = session.exec(select(User).where(User.google_sub == identity.sub)).first()
    if user is None:
        user = session.exec(select(User).where(User.email == email)).first()
        if user is not None and user.google_sub is not None:
            # Otra cuenta de Google que ya usó este email (caso raro: el email cambió de dueño).
            raise HTTPException(status.HTTP_409_CONFLICT, "Ese email ya está en uso")
        if user is not None:
            # Cuenta con contraseña y el mismo email: se une a esta cuenta de Google y se BORRA
            # la contraseña. Como el registro no confirma el email, otra persona podría haberlo
            # registrado antes; así no conserva el acceso. Si era tuya, la recuperas por email.
            user.google_sub = identity.sub
            user.password_hash = None
            invalidate_reset_tokens(session, user)
        else:
            user = User(google_sub=identity.sub, email=email, name=identity.name)
    # Nombre, email y foto se refrescan en cada login por si cambiaron en Google (el email solo
    # si no lo usa ya otra cuenta).
    email_taken = session.exec(select(User).where(User.email == email, User.id != user.id)).first()
    if email_taken is None:
        user.email = email
    user.name = identity.name
    user.avatar_url = identity.picture
    session.add(user)
    session.commit()
    session.refresh(user)

    set_session_cookie(response, user)
    return user_read(user)


# --- Sesión y cuenta ---


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Borra la cookie de sesión."""
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


@router.get("/me")
def me(user: CurrentUser) -> UserRead:
    """Usuario de la sesión actual (401 si no hay)."""
    return user_read(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(response: Response, session: SessionDep, user: CurrentUser) -> None:
    """Eliminar mi cuenta: anonimiza mis datos y cierra la sesión (ver services/account.py)."""
    delete_account(session, user)
    logout(response)
