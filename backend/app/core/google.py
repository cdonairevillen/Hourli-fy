"""Verificación del ID token que devuelve el botón "Iniciar sesión con Google"."""

from collections.abc import Callable
from dataclasses import dataclass

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import settings


@dataclass
class GoogleIdentity:
    """Datos de la cuenta de Google que nos interesan."""

    sub: str
    email: str
    email_verified: bool
    name: str
    picture: str | None


class GoogleLoginError(Exception):
    """El ID token no es válido (firma, caducidad, audiencia...)."""


def verify_google_credential(credential: str) -> GoogleIdentity:
    """Comprueba firma, caducidad y que el token sea para nuestro Client ID."""
    try:
        claims = id_token.verify_oauth2_token(
            credential, google_requests.Request(), settings.google_client_id
        )
    except ValueError as error:
        raise GoogleLoginError(str(error)) from error
    return GoogleIdentity(
        sub=claims["sub"],
        email=claims["email"],
        email_verified=bool(claims.get("email_verified")),
        name=claims.get("name") or claims["email"],
        picture=claims.get("picture"),
    )


def get_google_verifier() -> Callable[[str], GoogleIdentity]:
    """Dependencia de FastAPI. Los tests la sustituyen por un verificador falso."""
    return verify_google_credential
