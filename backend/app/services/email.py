"""Envío de emails. En local se escriben en la consola; en producción salen por SMTP o Resend."""

import logging
import smtplib
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage

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


def send_with_smtp(message: EmailMessage) -> None:
    """Envía el email por SMTP con SSL (p. ej. Gmail: smtp.gmail.com:465).

    Con Gmail, EMAIL_FROM tiene que ser la misma cuenta que SMTP_USER y la contraseña es una
    "contraseña de aplicación" (no la de la cuenta).
    """
    mime = MimeMessage()
    mime["From"] = settings.email_from
    mime["To"] = message.to
    mime["Subject"] = message.subject
    mime.set_content(message.text)
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(mime)


def get_email_sender() -> EmailSender:
    """Dependencia de FastAPI: los tests la cambian por una que guarda los emails en una lista."""
    if settings.email_backend == "resend":
        return send_with_resend
    if settings.email_backend == "smtp":
        return send_with_smtp
    return send_to_console


def send_safely(send: EmailSender, message: EmailMessage) -> None:
    """Envía sin romper la petición si el servicio de email falla: se registra el error.

    Así "recuperar contraseña" responde igual exista o no la cuenta, y no da pistas.
    """
    try:
        send(message)
    except Exception:
        logger.exception("No se pudo enviar el email a %s", message.to)
