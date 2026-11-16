"""Envío de emails por SMTP (Gmail) sin red: se sustituye el servidor por uno falso."""

import pytest

from app.core.config import settings
from app.services import email
from app.services.email import EmailMessage, get_email_sender, send_with_smtp


class FakeSMTP:
    """Hace de smtplib.SMTP_SSL y apunta a qué servidor se conecta, con qué login y qué envía."""

    sent: list = []

    def __init__(self, host: str, port: int, timeout: int):
        self.address = (host, port)
        # Credenciales con las que se hizo login (None hasta llamar a login).
        self.credentials = None
        FakeSMTP.last = self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def login(self, user: str, password: str) -> None:
        self.credentials = (user, password)

    def send_message(self, message) -> None:
        FakeSMTP.sent.append(message)


@pytest.fixture
def fake_smtp(monkeypatch: pytest.MonkeyPatch) -> type[FakeSMTP]:
    FakeSMTP.sent = []
    monkeypatch.setattr(email.smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setattr(settings, "smtp_user", "hourlify@gmail.com")
    monkeypatch.setattr(settings, "smtp_password", "clave-de-aplicacion")
    monkeypatch.setattr(settings, "email_from", "Hourli-fy <hourlify@gmail.com>")
    return FakeSMTP


def test_smtp_envia_el_email_con_login(fake_smtp):
    send_with_smtp(
        EmailMessage(to="ana@hotmail.com", subject="Recupera tu contraseña", text="Hola")
    )

    assert fake_smtp.last.address == ("smtp.gmail.com", 465)
    assert fake_smtp.last.credentials == ("hourlify@gmail.com", "clave-de-aplicacion")
    sent = fake_smtp.sent[-1]
    assert sent["To"] == "ana@hotmail.com"
    assert sent["From"] == "Hourli-fy <hourlify@gmail.com>"
    assert sent["Subject"] == "Recupera tu contraseña"
    assert sent.get_content().strip() == "Hola"


def test_email_backend_elige_el_envio(monkeypatch: pytest.MonkeyPatch):
    for backend, sender in [
        ("smtp", email.send_with_smtp),
        ("resend", email.send_with_resend),
        ("console", email.send_to_console),
    ]:
        monkeypatch.setattr(settings, "email_backend", backend)
        assert get_email_sender() is sender


def test_recuperar_contrasena_por_smtp_de_punta_a_punta(make_client, fake_smtp):
    """La ruta real con el envío SMTP (sin la lista de los demás tests)."""
    from app.main import app

    client = make_client()
    client.post(
        "/api/auth/register",
        json={"name": "Ana", "email": "ana@hotmail.com", "password": "una-contraseña-larga"},
    )
    app.dependency_overrides[get_email_sender] = lambda: send_with_smtp

    response = client.post("/api/auth/password/forgot", json={"email": "ana@hotmail.com"})

    assert response.status_code == 202
    assert "/recuperar/" in fake_smtp.sent[-1].get_content()
