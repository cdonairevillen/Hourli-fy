from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.google import GoogleIdentity, GoogleLoginError, get_google_verifier
from app.core.security import SESSION_COOKIE, create_session_token
from app.models import User
from app.schemas import GoogleLogin, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

GoogleVerifier = Annotated[Callable[[str], GoogleIdentity], Depends(get_google_verifier)]


def user_read(user: User) -> UserRead:
    return UserRead(id=user.id, name=user.name, email=user.email, avatar_url=user.avatar_url)


@router.post("/google")
def login_with_google(
    body: GoogleLogin, response: Response, session: SessionDep, verify: GoogleVerifier
) -> UserRead:
    """Recibe el ID token de Google, crea el usuario si es su primera vez y pone la cookie."""
    if not settings.google_client_id:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Falta GOOGLE_CLIENT_ID")
    try:
        identity = verify(body.credential)
    except GoogleLoginError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de Google no válido") from error
    if not identity.email_verified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "El email de Google no está verificado")

    user = session.exec(select(User).where(User.google_sub == identity.sub)).first()
    if user is None:
        # Otra cuenta de Google que ya usó este email (caso raro: el email cambió de dueño).
        taken = session.exec(select(User).where(User.email == identity.email)).first()
        if taken is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Ese email ya está en uso")
        user = User(google_sub=identity.sub, email=identity.email, name=identity.name)
    # Nombre, email y foto se refrescan en cada login por si cambiaron en Google.
    user.email = identity.email
    user.name = identity.name
    user.avatar_url = identity.picture
    session.add(user)
    session.commit()
    session.refresh(user)

    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user.id),
        max_age=settings.session_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    return user_read(user)


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
