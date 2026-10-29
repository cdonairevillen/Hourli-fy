import re
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import PasswordResetToken, User
from app.models.common import utc_now
from tests.test_workspaces import create_workspace

PASSWORD = "una-contraseña-larga"


def register(client: TestClient, email: str = "ana@hotmail.com", password: str = PASSWORD):
    return client.post(
        "/api/auth/register", json={"name": "Ana", "email": email, "password": password}
    )


def login(client: TestClient, email: str = "ana@hotmail.com", password: str = PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def reset_link_token(outbox) -> str:
    """El token del último email de recuperación (lo que el usuario pincharía)."""
    match = re.search(r"/recuperar/(\S+)", outbox[-1].text)
    assert match, outbox[-1].text
    return match[1]


# --- Registro y login ---


def test_registro_con_cualquier_dominio_abre_sesion(make_client, db: Session):
    client = make_client()

    response = register(client, "Ana.Perez@Hotmail.com")

    assert response.status_code == 201
    assert response.json()["email"] == "ana.perez@hotmail.com"
    assert response.json()["has_password"] is True
    assert client.get("/api/auth/me").status_code == 200
    stored = db.exec(select(User).where(User.email == "ana.perez@hotmail.com")).one()
    # En la BD solo está el hash (argon2), nunca la contraseña.
    assert stored.password_hash.startswith("$argon2")
    assert PASSWORD not in stored.password_hash


def test_registrado_puede_usar_la_app(make_client):
    client = make_client()
    register(client)

    assert create_workspace(client)["is_owner"] is True


def test_email_repetido_da_409_aunque_cambien_mayusculas(make_client):
    register(make_client(), "ana@outlook.com")

    response = register(make_client(), "ANA@Outlook.com")

    assert response.status_code == 409


def test_no_se_puede_registrar_un_email_de_una_cuenta_de_google(make_client):
    make_client("ana")  # entra con Google como ana@example.com

    assert register(make_client(), "ana@example.com").status_code == 409


def test_contrasena_corta_o_email_invalido_dan_422(make_client):
    client = make_client()

    assert register(client, password="corta").status_code == 422
    assert register(client, email="no-es-un-email").status_code == 422


def test_login_correcto(make_client):
    register(make_client())
    client = make_client()

    response = login(client, "ANA@hotmail.com")

    assert response.status_code == 200
    assert client.get("/api/auth/me").json()["email"] == "ana@hotmail.com"


def test_login_incorrecto_no_dice_que_fallo(make_client):
    register(make_client())

    wrong_password = login(make_client(), password="otra-contraseña")
    unknown_email = login(make_client(), email="nadie@hotmail.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_cuenta_de_google_sin_contrasena_no_entra_con_contrasena(make_client):
    make_client("ana")

    assert login(make_client(), "ana@example.com", "lo-que-sea-123").status_code == 401


def test_demasiados_intentos_dan_429(make_client):
    register(make_client())
    client = make_client()
    for _ in range(10):
        login(client, password="mal-mal-mal")

    response = login(client)

    assert response.status_code == 429


def test_cuenta_eliminada_no_entra(make_client):
    client = make_client()
    register(client)
    client.delete("/api/auth/me")

    assert login(make_client()).status_code == 401


# --- Recuperar la contraseña ---


def test_recuperar_contrasena_con_el_link_del_email(make_client, outbox):
    register(make_client())
    client = make_client()

    forgot = client.post("/api/auth/password/forgot", json={"email": "Ana@Hotmail.com"})
    token = reset_link_token(outbox)
    reset = client.post(
        "/api/auth/password/reset", json={"token": token, "password": "nueva-contraseña"}
    )

    assert forgot.status_code == 202
    assert outbox[-1].to == "ana@hotmail.com"
    assert "http://localhost:5173/recuperar/" in outbox[-1].text
    assert reset.status_code == 200
    # El reset abre la sesión, y la contraseña nueva vale para entrar; la vieja ya no.
    assert client.get("/api/auth/me").status_code == 200
    assert login(make_client(), password="nueva-contraseña").status_code == 200
    assert login(make_client()).status_code == 401


def test_email_sin_cuenta_responde_igual_y_no_envia_nada(make_client, outbox):
    response = make_client().post("/api/auth/password/forgot", json={"email": "x@hotmail.com"})

    assert response.status_code == 202
    assert outbox == []


def test_el_link_solo_sirve_una_vez(make_client, outbox):
    register(make_client())
    client = make_client()
    client.post("/api/auth/password/forgot", json={"email": "ana@hotmail.com"})
    token = reset_link_token(outbox)
    body = {"token": token, "password": "nueva-contraseña"}

    assert client.post("/api/auth/password/reset", json=body).status_code == 200
    assert client.post("/api/auth/password/reset", json=body).status_code == 410


def test_el_link_caduca(make_client, outbox, db: Session):
    register(make_client())
    client = make_client()
    client.post("/api/auth/password/forgot", json={"email": "ana@hotmail.com"})
    token = reset_link_token(outbox)
    reset = db.exec(select(PasswordResetToken)).one()
    reset.expires_at = utc_now() - timedelta(seconds=1)
    db.commit()

    response = client.post(
        "/api/auth/password/reset", json={"token": token, "password": "nueva-contraseña"}
    )

    assert response.status_code == 410


def test_usar_un_link_gasta_los_demas(make_client, outbox):
    register(make_client())
    client = make_client()
    client.post("/api/auth/password/forgot", json={"email": "ana@hotmail.com"})
    first = reset_link_token(outbox)
    client.post("/api/auth/password/forgot", json={"email": "ana@hotmail.com"})
    second = reset_link_token(outbox)

    client.post("/api/auth/password/reset", json={"token": second, "password": "nueva-1-abc"})
    response = client.post(
        "/api/auth/password/reset", json={"token": first, "password": "nueva-2-abc"}
    )

    assert response.status_code == 410


def test_link_inventado_da_410(make_client):
    response = make_client().post(
        "/api/auth/password/reset", json={"token": "inventado", "password": "nueva-contraseña"}
    )

    assert response.status_code == 410


def test_como_mucho_3_emails_de_recuperacion_por_hora(make_client, outbox):
    register(make_client())
    client = make_client()
    for _ in range(3):
        client.post("/api/auth/password/forgot", json={"email": "ana@hotmail.com"})

    response = client.post("/api/auth/password/forgot", json={"email": "ana@hotmail.com"})

    assert response.status_code == 429
    assert len(outbox) == 3


# --- Cambiar o poner contraseña ---


def test_cambiar_contrasena_pide_la_actual(make_client):
    client = make_client()
    register(client)

    wrong = client.post(
        "/api/auth/password", json={"current_password": "mal", "new_password": "nueva-contraseña"}
    )
    right = client.post(
        "/api/auth/password",
        json={"current_password": PASSWORD, "new_password": "nueva-contraseña"},
    )

    assert wrong.status_code == 400
    assert right.status_code == 204
    assert login(make_client(), password="nueva-contraseña").status_code == 200


def test_cuenta_de_google_puede_ponerse_contrasena(make_client):
    ana = make_client("ana")

    response = ana.post("/api/auth/password", json={"new_password": "mi-contraseña-nueva"})

    assert response.status_code == 204
    assert ana.get("/api/auth/me").json()["has_password"] is True
    assert login(make_client(), "ana@example.com", "mi-contraseña-nueva").status_code == 200


def test_cambiar_contrasena_sin_sesion_da_401(make_client):
    response = make_client().post("/api/auth/password", json={"new_password": "nueva-contraseña"})

    assert response.status_code == 401


# --- Google y contraseña en la misma persona ---


def test_entrar_con_google_une_la_cuenta_y_borra_la_contrasena(make_client):
    """Sin confirmación de email, la contraseña podría ser de otra persona que registró tu email
    antes que tú: al unir con Google se borra, para que no conserve el acceso."""
    impostor = make_client()
    register(impostor, "ana@example.com")
    first_id = impostor.get("/api/auth/me").json()["id"]

    ana = make_client("ana")  # entra con Google con ana@example.com

    me = ana.get("/api/auth/me").json()
    assert me["id"] == first_id
    assert me["has_password"] is False
    assert login(make_client(), "ana@example.com").status_code == 401
