from sqlmodel import Session, select

from app.models import User


def test_login_crea_usuario_y_pone_cookie(make_client, db: Session):
    client = make_client()

    response = client.post("/api/auth/google", json={"credential": "sub-ana|ana@example.com|Ana"})

    assert response.status_code == 200
    assert response.json()["email"] == "ana@example.com"
    assert "session" in client.cookies
    assert db.exec(select(User).where(User.google_sub == "sub-ana")).one().name == "Ana"


def test_segundo_login_reutiliza_usuario_y_refresca_datos(make_client, db: Session):
    make_client("ana")
    client = make_client()

    client.post("/api/auth/google", json={"credential": "sub-ana|ana@example.com|Ana María"})

    users = db.exec(select(User).where(User.google_sub == "sub-ana")).all()
    assert len(users) == 1
    assert users[0].name == "Ana María"


def test_login_con_token_invalido_da_401(make_client):
    response = make_client().post("/api/auth/google", json={"credential": "basura"})

    assert response.status_code == 401


def test_login_sin_client_id_configurado_da_503(make_client, monkeypatch):
    from app.core.config import settings

    client = make_client()
    monkeypatch.setattr(settings, "google_client_id", "")

    response = client.post("/api/auth/google", json={"credential": "sub-ana|ana@example.com|Ana"})

    assert response.status_code == 503


def test_me_devuelve_el_usuario_de_la_sesion(make_client):
    response = make_client("ana").get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["name"] == "Ana"


def test_me_sin_sesion_da_401(make_client):
    assert make_client().get("/api/auth/me").status_code == 401


def test_me_con_cookie_falsificada_da_401(make_client):
    client = make_client()
    client.cookies.set("session", "no-es-un-jwt")

    assert client.get("/api/auth/me").status_code == 401


def test_logout_borra_la_sesion(make_client):
    client = make_client("ana")

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
