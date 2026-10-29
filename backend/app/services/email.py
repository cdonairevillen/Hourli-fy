"""Envío de emails. En local se escriben en la consola; en producción salen por Resend."""

import logging
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


@dataclass
class EmailMessage:
    to: str
    subject: str
    text: str


EmailSender = Callable[[EmailMessage], None]


def send_to_console(message: EmailMessage) -> None:
    """No envía nada: lo imprime para poder copiar el link al probar en local."""
    print(
        f"\n===== EMAIL (no enviado: EMAIL_BACKEND=console) =====\n"
        f"Para: {message.to}\nAsunto: {message.subject}\n\n{message.text}\n"
        f"=====================================================\n",
        flush=True,
    )


def send_with_resend(message: EmailMessage) -> None:
    """Envía el email con la API de Resend (https://resend.com/docs/api-reference/emails)."""
    response = httpx.post(
        RESEND_URL,
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={
            "from": settings.email_from,
            "to": [message.to],
            "subject": message.subject,
            "text": message.text,
        },
        timeout=10,
    )
    response.raise_for_status()


def get_email_sender() -> EmailSender:
    """Dependencia de FastAPI: los tests la cambian por una que guarda los emails en una lista."""
    if settings.email_backend == "resend":
        return send_with_resend
    return send_to_console


def send_safely(send: EmailSender, message: EmailMessage) -> None:
    """Envía sin romper la petición si el servicio de email falla: se registra el error.

    Así "recuperar contraseña" responde igual exista o no la cuenta, y no da pistas.
    """
    try:
        send(message)
    except Exception:
        logger.exception("No se pudo enviar el email a %s", message.to)
