from sqlmodel import Session, select

from app.models import TimeEntry, User
from tests.test_entries import create_manual, setup_workspace, task
from tests.test_workspaces import create_workspace, join, user_id


def test_eliminar_cuenta_anonimiza_y_cierra_sesion(make_client, db: Session):
    bea = make_client("bea")
    bea_id = user_id(bea)

    response = bea.delete("/api/auth/me")

    assert response.status_code == 204
    assert bea.get("/api/auth/me").status_code == 401
    user = db.exec(select(User).where(User.id == bea_id)).one()
    assert user.name == "Usuario eliminado"
    assert "bea" not in user.email
    assert user.google_sub != "sub-bea"
    assert user.deleted_at is not None


def test_con_espacios_propios_activos_da_409(make_client):
    ana = make_client("ana")
    create_workspace(ana, "Estudio Ana")

    response = ana.delete("/api/auth/me")

    assert response.status_code == 409
    assert "Estudio Ana" in response.json()["detail"]
    assert ana.get("/api/auth/me").status_code == 200


def test_con_espacios_propios_archivados_si_se_puede(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    ana.patch(f"/api/workspaces/{wid}", json={"archived": True})

    assert ana.delete("/api/auth/me").status_code == 204


def test_sus_horas_siguen_en_el_panel_sin_nombre(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    ws = setup_workspace(ana)
    join(ana, bea, ws["wid"])
    create_manual(bea, ws, "2026-10-05T08:00:00Z", "2026-10-05T10:00:00Z")

    bea.delete("/api/auth/me")
    summary = ana.get(
        f"/api/workspaces/{ws['wid']}/reports/summary", params={"period": "2026-10-A"}
    ).json()

    assert [(u["name"], u["total_seconds"]) for u in summary["by_user"]] == [
        ("Usuario eliminado", 7200)
    ]
    members = ana.get(f"/api/workspaces/{ws['wid']}/members").json()
    assert [m["name"] for m in members] == ["Ana"]


def test_se_para_su_cronometro(make_client, db: Session):
    ana, bea = make_client("ana"), make_client("bea")
    ws = setup_workspace(ana)
    join(ana, bea, ws["wid"])
    bea.post(f"/api/workspaces/{ws['wid']}/timer/start", json=task(ws))

    bea.delete("/api/auth/me")

    assert db.exec(select(TimeEntry).where(TimeEntry.end_at.is_(None))).all() == []


def test_volver_a_entrar_con_google_crea_un_usuario_nuevo(make_client):
    bea = make_client("bea")
    old_id = user_id(bea)
    bea.delete("/api/auth/me")

    again = make_client("bea")

    assert user_id(again) != old_id
    assert again.get("/api/auth/me").json()["name"] == "Bea"


def test_sin_sesion_da_401(make_client):
    assert make_client().delete("/api/auth/me").status_code == 401
