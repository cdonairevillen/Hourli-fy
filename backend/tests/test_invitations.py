from datetime import timedelta

from sqlmodel import Session, select

from app.models import Invitation
from app.models.common import utc_now
from tests.test_workspaces import create_workspace, join, user_id


def create_invitation(client, wid: str, **body) -> dict:
    response = client.post(f"/api/workspaces/{wid}/invitations", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_crear_invitacion_devuelve_token_y_caduca_en_10_dias(make_client, db: Session):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]

    invitation = create_invitation(ana, wid)

    assert invitation["status"] == "active"
    assert len(invitation["token"]) >= 40
    stored = db.exec(select(Invitation)).one()
    # En la BD no queda el token, solo su hash.
    assert stored.token_hash != invitation["token"]
    assert timedelta(days=9, hours=23) < stored.expires_at - utc_now() <= timedelta(days=10)


def test_el_listado_no_incluye_el_token(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    create_invitation(ana, wid)

    listed = ana.get(f"/api/workspaces/{wid}/invitations").json()

    assert len(listed) == 1
    assert "token" not in listed[0]


def test_solo_la_duena_crea_y_lista_invitaciones(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)

    assert bea.post(f"/api/workspaces/{wid}/invitations", json={}).status_code == 403
    assert bea.get(f"/api/workspaces/{wid}/invitations").status_code == 403


def test_vista_previa_publica(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana, "Estudio Ana")["id"]
    token = create_invitation(ana, wid)["token"]

    response = make_client().get(f"/api/invitations/{token}")

    assert response.status_code == 200
    assert response.json()["workspace_name"] == "Estudio Ana"
    assert response.json()["owner_name"] == "Ana"
    assert response.json()["status"] == "active"


def test_token_desconocido_da_404(make_client):
    assert make_client().get("/api/invitations/no-existe").status_code == 404
    assert make_client("bea").post("/api/invitations/no-existe/accept").status_code == 404


def test_aceptar_sin_sesion_da_401(make_client):
    ana = make_client("ana")
    token = create_invitation(ana, create_workspace(ana)["id"])["token"]

    assert make_client().post(f"/api/invitations/{token}/accept").status_code == 401


def test_aceptar_une_al_espacio_y_cuenta_un_uso(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    token = create_invitation(ana, wid)["token"]

    response = bea.post(f"/api/invitations/{token}/accept")

    assert response.status_code == 200
    assert response.json()["is_owner"] is False
    assert [w["id"] for w in bea.get("/api/workspaces").json()] == [wid]
    assert ana.get(f"/api/workspaces/{wid}/invitations").json()[0]["uses"] == 1


def test_aceptar_siendo_ya_miembro_no_gasta_uso(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    token = create_invitation(ana, wid, max_uses=2)["token"]
    bea.post(f"/api/invitations/{token}/accept")

    assert bea.post(f"/api/invitations/{token}/accept").status_code == 200
    assert ana.post(f"/api/invitations/{token}/accept").status_code == 200
    assert ana.get(f"/api/workspaces/{wid}/invitations").json()[0]["uses"] == 1


def test_max_uses_agota_el_link(make_client):
    ana, bea, cris = make_client("ana"), make_client("bea"), make_client("cris")
    wid = create_workspace(ana)["id"]
    token = create_invitation(ana, wid, max_uses=1)["token"]

    assert bea.post(f"/api/invitations/{token}/accept").status_code == 200
    assert cris.post(f"/api/invitations/{token}/accept").status_code == 410
    assert make_client().get(f"/api/invitations/{token}").json()["status"] == "exhausted"


def test_invitacion_caducada_no_sirve(make_client, db: Session):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    token = create_invitation(ana, wid)["token"]
    stored = db.exec(select(Invitation)).one()
    stored.expires_at = utc_now() - timedelta(seconds=1)
    db.add(stored)
    db.commit()

    assert bea.post(f"/api/invitations/{token}/accept").status_code == 410
    assert make_client().get(f"/api/invitations/{token}").json()["status"] == "expired"


def test_revocar_invitacion(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    invitation = create_invitation(ana, wid)

    response = ana.delete(f"/api/workspaces/{wid}/invitations/{invitation['id']}")

    assert response.status_code == 204
    assert bea.post(f"/api/invitations/{invitation['token']}/accept").status_code == 410
    assert ana.get(f"/api/workspaces/{wid}/invitations").json()[0]["status"] == "revoked"


def test_no_se_revoca_una_invitacion_de_otro_espacio(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid_ana = create_workspace(ana)["id"]
    wid_bea = create_workspace(bea)["id"]
    invitation_bea = create_invitation(bea, wid_bea)

    response = ana.delete(f"/api/workspaces/{wid_ana}/invitations/{invitation_bea['id']}")

    assert response.status_code == 404
    assert bea.get(f"/api/workspaces/{wid_bea}/invitations").json()[0]["status"] == "active"


def test_espacio_archivado_invalida_links_y_no_crea_nuevos(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    token = create_invitation(ana, wid)["token"]
    ana.patch(f"/api/workspaces/{wid}", json={"archived": True})

    assert bea.post(f"/api/invitations/{token}/accept").status_code == 410
    assert ana.post(f"/api/workspaces/{wid}/invitations", json={}).status_code == 409


def test_expulsado_puede_volver_con_un_link_nuevo(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)
    ana.delete(f"/api/workspaces/{wid}/members/{user_id(bea)}")

    token = create_invitation(ana, wid)["token"]

    assert bea.post(f"/api/invitations/{token}/accept").status_code == 200
    assert len(ana.get(f"/api/workspaces/{wid}/members").json()) == 2
