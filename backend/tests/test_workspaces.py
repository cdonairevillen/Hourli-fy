from fastapi.testclient import TestClient


def create_workspace(client: TestClient, name: str = "Estudio") -> dict:
    response = client.post("/api/workspaces", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def join(owner: TestClient, guest: TestClient, wid: str) -> None:
    """El dueño crea un link y el invitado lo acepta."""
    token = owner.post(f"/api/workspaces/{wid}/invitations", json={}).json()["token"]
    assert guest.post(f"/api/invitations/{token}/accept").status_code == 200


def user_id(client: TestClient) -> str:
    return client.get("/api/auth/me").json()["id"]


def test_crear_espacio_me_hace_duena_y_miembro(make_client):
    ana = make_client("ana")

    workspace = create_workspace(ana)

    assert workspace["is_owner"] is True
    assert [w["id"] for w in ana.get("/api/workspaces").json()] == [workspace["id"]]
    members = ana.get(f"/api/workspaces/{workspace['id']}/members").json()
    assert [(m["name"], m["is_owner"]) for m in members] == [("Ana", True)]


def test_crear_espacio_sin_sesion_da_401(make_client):
    assert make_client().post("/api/workspaces", json={"name": "X"}).status_code == 401


def test_nombre_vacio_da_422(make_client):
    assert make_client("ana").post("/api/workspaces", json={"name": ""}).status_code == 422


def test_limite_de_cinco_espacios_propios(make_client):
    ana = make_client("ana")
    for number in range(5):
        create_workspace(ana, f"Espacio {number}")

    response = ana.post("/api/workspaces", json={"name": "Sexto"})

    assert response.status_code == 409


def test_archivar_libera_hueco_y_desarchivar_respeta_el_limite(make_client):
    ana = make_client("ana")
    workspaces = [create_workspace(ana, f"Espacio {number}") for number in range(5)]
    first = workspaces[0]["id"]

    archived = ana.patch(f"/api/workspaces/{first}", json={"archived": True})
    assert archived.json()["archived"] is True
    create_workspace(ana, "Sexto")

    assert ana.patch(f"/api/workspaces/{first}", json={"archived": False}).status_code == 409


def test_espacios_invitados_no_cuentan_en_el_limite(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    for number in range(5):
        join(bea, ana, create_workspace(bea, f"De Bea {number}")["id"])

    create_workspace(ana, "Mío")

    assert len(ana.get("/api/workspaces").json()) == 6


def test_renombrar_espacio(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]

    response = ana.patch(f"/api/workspaces/{wid}", json={"name": "Nuevo nombre"})

    assert response.status_code == 200
    assert response.json()["name"] == "Nuevo nombre"


def test_miembro_no_puede_editar_el_espacio(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)

    assert bea.patch(f"/api/workspaces/{wid}", json={"name": "Mío"}).status_code == 403


def test_transferir_propiedad(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)

    response = ana.patch(f"/api/workspaces/{wid}", json={"owner_id": user_id(bea)})

    assert response.status_code == 200
    assert response.json()["is_owner"] is False
    assert bea.get("/api/workspaces").json()[0]["is_owner"] is True
    assert ana.patch(f"/api/workspaces/{wid}", json={"name": "X"}).status_code == 403


def test_transferir_a_quien_no_es_miembro_da_422(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]

    response = ana.patch(f"/api/workspaces/{wid}", json={"owner_id": user_id(bea)})

    assert response.status_code == 422


def test_transferir_a_quien_ya_tiene_cinco_da_409(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)
    for number in range(5):
        create_workspace(bea, f"De Bea {number}")

    response = ana.patch(f"/api/workspaces/{wid}", json={"owner_id": user_id(bea)})

    assert response.status_code == 409


def test_miembro_puede_salir(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)

    assert bea.delete(f"/api/workspaces/{wid}/members/{user_id(bea)}").status_code == 204
    assert bea.get("/api/workspaces").json() == []
    assert bea.get(f"/api/workspaces/{wid}/members").status_code == 404


def test_duena_expulsa_a_un_miembro(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)

    assert ana.delete(f"/api/workspaces/{wid}/members/{user_id(bea)}").status_code == 204
    members = ana.get(f"/api/workspaces/{wid}/members").json()
    assert [m["name"] for m in members] == ["Ana"]


def test_miembro_no_puede_expulsar(make_client):
    ana, bea, cris = make_client("ana"), make_client("bea"), make_client("cris")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)
    join(ana, cris, wid)

    response = bea.delete(f"/api/workspaces/{wid}/members/{user_id(cris)}")

    assert response.status_code == 403


def test_la_duena_no_puede_salir_sin_transferir(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]

    assert ana.delete(f"/api/workspaces/{wid}/members/{user_id(ana)}").status_code == 409


# --- Aislamiento: nadie ve ni toca un espacio del que no es miembro ---


def test_ajeno_no_ve_ni_toca_el_espacio(make_client):
    ana, intruso = make_client("ana"), make_client("intruso")
    wid = create_workspace(ana)["id"]

    assert intruso.get("/api/workspaces").json() == []
    assert intruso.get(f"/api/workspaces/{wid}/members").status_code == 404
    assert intruso.patch(f"/api/workspaces/{wid}", json={"name": "X"}).status_code == 404
    assert intruso.get(f"/api/workspaces/{wid}/invitations").status_code == 404
    assert intruso.post(f"/api/workspaces/{wid}/invitations", json={}).status_code == 404
    assert intruso.delete(f"/api/workspaces/{wid}/members/{user_id(ana)}").status_code == 404


def test_espacio_inexistente_da_404(make_client):
    ana = make_client("ana")

    response = ana.get("/api/workspaces/00000000-0000-0000-0000-000000000000/members")

    assert response.status_code == 404
