import re
import uuid

import pytest
from fastapi.testclient import TestClient

from app.admin import ADMIN_VIEWS
from app.core.config import settings
from tests.test_clockify_pdf import build_clockify_pdf
from tests.test_entries import create_manual, setup_workspace
from tests.test_imports import BASIC, BASIC_TOTAL, members_by_name
from tests.test_workspaces import create_workspace


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


# --- Importador de Clockify en el panel ---


def admin_import(client: TestClient, wid: str) -> str:
    """Sube el PDF, comprueba la vista previa y confirma. Devuelve la página del resultado."""
    pdf = build_clockify_pdf(BASIC, total=BASIC_TOTAL)
    page = client.post(
        "/admin/import",
        data={"step": "preview", "workspace_id": wid, "project_name": "Proyecto Lorca"},
        files={"file": ("informe.pdf", pdf, "application/pdf")},
    )
    assert page.status_code == 200, page.text
    assert "Irene Félix" in page.text and "Bea Ruiz" in page.text
    encoded = re.search(r'name="pdf" value="([^"]+)"', page.text)[1]
    result = client.post(
        "/admin/import",
        data={
            "step": "confirm",
            "workspace_id": wid,
            "project_name": "Proyecto Lorca",
            "pdf": encoded,
            "person_name": ["Bea Ruiz", "Irene Félix"],
            "person_user": ["", ""],
        },
    )
    assert result.status_code == 200, result.text
    return result.text


def test_admin_importa_un_pdf_en_cualquier_espacio(make_client, admin_email):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(bea, "Estudio de Bea")["id"]

    form = get(ana, "/admin/import")
    result = admin_import(ana, wid)

    assert form.status_code == 200
    assert "Estudio de Bea" in form.text
    assert "3 registros nuevos" in result
    assert members_by_name(bea, wid)["Irene Félix"]["is_ghost"] is True


def test_admin_importador_con_pdf_que_no_cuadra(make_client, admin_email):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    pdf = build_clockify_pdf(BASIC, total="9:00:00")

    page = ana.post(
        "/admin/import",
        data={"step": "preview", "workspace_id": wid, "project_name": "Proyecto Lorca"},
        files={"file": ("informe.pdf", pdf, "application/pdf")},
    )

    assert page.status_code == 400
    assert "no se importa nada" in page.text


def test_usuario_normal_no_entra_al_importador(make_client, admin_email):
    response = get(make_client("bea"), "/admin/import")

    assert response.status_code in (302, 303)


def test_admin_genera_link_para_reclamar_un_fantasma(make_client, admin_email):
    ana, irene = make_client("ana"), make_client("irene")
    wid = create_workspace(ana)["id"]
    admin_import(ana, wid)
    ghost_id = members_by_name(ana, wid)["Irene Félix"]["user_id"]

    page = get(ana, f"/admin/user/action/claim-link?pks={ghost_id}")
    token = re.search(r"/invite/([\w-]+)", page.text)[1]
    accepted = irene.post(f"/api/invitations/{token}/accept")

    assert page.status_code == 200
    assert accepted.status_code == 200
    assert "Irene" in members_by_name(ana, wid)


def test_fantasmas_sin_link_de_recuperacion_y_reclamar_solo_fantasmas(make_client, admin_email):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    admin_import(ana, wid)
    ghost_id = members_by_name(ana, wid)["Bea Ruiz"]["user_id"]
    ana_id = ana.get("/api/auth/me").json()["id"]

    assert get(ana, f"/admin/user/action/reset-link?pks={ghost_id}").status_code == 409
    assert get(ana, f"/admin/user/action/claim-link?pks={ana_id}").status_code == 404
