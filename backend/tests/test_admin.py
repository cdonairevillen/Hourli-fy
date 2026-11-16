import re
import uuid

import pytest
from fastapi.testclient import TestClient

from app.admin import ADMIN_VIEWS
from app.core.config import settings
from tests.test_entries import create_manual, setup_workspace


@pytest.fixture
def admin_email(monkeypatch: pytest.MonkeyPatch) -> str:
    """Ana (ana@example.com) es admin en estos tests."""
    monkeypatch.setattr(settings, "admin_emails", ["ANA@example.com"])
    return "ana@example.com"


def get(client: TestClient, path: str):
    return client.get(path, follow_redirects=False)


def test_sin_sesion_redirige_al_login_del_panel(make_client, admin_email):
    response = get(make_client(), "/admin/")

    assert response.status_code in (302, 303)
    assert "/admin/login" in response.headers["location"]


def test_usuario_normal_no_entra(make_client, admin_email):
    bea = make_client("bea")

    response = get(bea, "/admin/")

    assert response.status_code in (302, 303)
    assert "/admin/login" in response.headers["location"]


def test_admin_con_su_sesion_de_la_app_entra(make_client, admin_email):
    ana = make_client("ana")

    response = get(ana, "/admin/")

    assert response.status_code == 200
    assert "Hourli-fy" in response.text


def test_admin_ve_la_lista_de_cada_tabla(make_client, admin_email):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z", title="Tarea visible")

    for view in ADMIN_VIEWS:
        response = get(ana, f"/admin/{view.identity}/list")
        assert response.status_code == 200, (view.identity, response.text[:300])
    tasks = get(ana, "/admin/time-entry/list")
    assert "Tarea visible" in tasks.text


def test_el_panel_no_muestra_hashes(make_client, admin_email):
    ana = make_client("ana")
    ana.post("/api/auth/password", json={"new_password": "contraseña-de-ana"})
    me = ana.get("/api/auth/me").json()

    detail = get(ana, f"/admin/user/details/{me['id']}")

    assert detail.status_code == 200
    assert "argon2" not in detail.text
    assert "sub-ana" not in detail.text


def test_login_del_panel_con_email_y_contrasena(make_client, admin_email):
    ana = make_client("ana")
    ana.post("/api/auth/password", json={"new_password": "contraseña-de-ana"})
    browser = make_client()

    wrong = browser.post(
        "/admin/login",
        data={"username": "ana@example.com", "password": "mal"},
        follow_redirects=False,
    )
    right = browser.post(
        "/admin/login",
        data={"username": "ana@example.com", "password": "contraseña-de-ana"},
        follow_redirects=False,
    )

    assert wrong.status_code == 400
    assert right.status_code in (302, 303)
    assert get(browser, "/admin/").status_code == 200


def test_login_del_panel_rechaza_a_quien_no_es_admin(make_client, admin_email):
    bea = make_client("bea")
    bea.post("/api/auth/password", json={"new_password": "contraseña-de-bea"})
    browser = make_client()

    response = browser.post(
        "/admin/login",
        data={"username": "bea@example.com", "password": "contraseña-de-bea"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert get(browser, "/admin/").status_code in (302, 303)


def test_admin_es_visible_en_me(make_client, admin_email):
    assert make_client("ana").get("/api/auth/me").json()["is_admin"] is True
    assert make_client("bea").get("/api/auth/me").json()["is_admin"] is False


def test_admin_genera_link_de_recuperacion_que_funciona(make_client, admin_email, outbox):
    """Si el email no llega, el admin saca un link y se lo pasa; el usuario elige su contraseña."""
    ana = make_client("ana")
    bea_id = make_client("bea").get("/api/auth/me").json()["id"]

    page = get(ana, f"/admin/user/action/reset-link?pks={bea_id}")

    assert page.status_code == 200
    assert "bea@example.com" in page.text
    token = re.search(r"/recuperar/([\w-]+)", page.text)[1]
    assert outbox == []  # no se manda ningún email: el link solo se enseña al admin
    reset = make_client().post(
        "/api/auth/password/reset", json={"token": token, "password": "nueva-de-bea"}
    )
    assert reset.status_code == 200
    login = make_client().post(
        "/api/auth/login", json={"email": "bea@example.com", "password": "nueva-de-bea"}
    )
    assert login.status_code == 200


def test_usuario_normal_no_genera_links_de_recuperacion(make_client, admin_email):
    bea = make_client("bea")
    ana_id = make_client("ana").get("/api/auth/me").json()["id"]

    response = get(bea, f"/admin/user/action/reset-link?pks={ana_id}")

    assert response.status_code in (302, 303)
    assert "/admin/login" in response.headers["location"]


def test_link_de_recuperacion_de_admin_con_usuario_inexistente(make_client, admin_email):
    ana = make_client("ana")

    assert get(ana, f"/admin/user/action/reset-link?pks={uuid.uuid4()}").status_code == 404
    assert get(ana, "/admin/user/action/reset-link?pks=").status_code == 400
