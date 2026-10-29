from fastapi.testclient import TestClient

from tests.test_catalog import create_project
from tests.test_entries import create_manual, setup_workspace, task
from tests.test_workspaces import join, user_id

TIMES = ("2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")


def company(make_client) -> tuple[TestClient, dict]:
    """Ana (dueña) con un espacio y dos proyectos: "Lorca" (el del setup) y "Cervantes"."""
    ana = make_client("ana")
    ws = setup_workspace(ana)
    ana.patch(f"/api/workspaces/{ws['wid']}/projects/{ws['project']}", json={"name": "Lorca"})
    ws["lorca"] = ws["project"]
    ws["cervantes"] = create_project(ana, ws["wid"], "Cervantes")["id"]
    return ana, ws


def invite(owner: TestClient, wid: str, project_id: str | None = None, **body) -> str:
    response = owner.post(
        f"/api/workspaces/{wid}/invitations", json={"project_id": project_id, **body}
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


def accept(client: TestClient, token: str):
    return client.post(f"/api/invitations/{token}/accept")


def visible_projects(client: TestClient, wid: str) -> list[str]:
    response = client.get(f"/api/workspaces/{wid}/projects")
    assert response.status_code == 200, response.text
    return sorted(p["name"] for p in response.json())


def invitation_uses(owner: TestClient, wid: str) -> list[int]:
    return [i["uses"] for i in owner.get(f"/api/workspaces/{wid}/invitations").json()]


# --- Invitación a un proyecto ---


def test_invitado_a_un_proyecto_solo_ve_ese(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    token = invite(ana, ws["wid"], ws["lorca"])

    preview = make_client().get(f"/api/invitations/{token}").json()
    accepted = accept(bea, token)

    assert preview["project_name"] == "Lorca"
    assert accepted.status_code == 200
    assert [w["id"] for w in bea.get("/api/workspaces").json()] == [ws["wid"]]
    assert visible_projects(bea, ws["wid"]) == ["Lorca"]
    assert visible_projects(ana, ws["wid"]) == ["Cervantes", "Lorca"]


def test_no_recibe_los_proyectos_que_se_crean_despues(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    accept(bea, invite(ana, ws["wid"], ws["lorca"]))

    create_project(ana, ws["wid"], "Quijote")

    assert visible_projects(bea, ws["wid"]) == ["Lorca"]


def test_registra_en_su_proyecto_pero_no_en_otro(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    accept(bea, invite(ana, ws["wid"], ws["lorca"]))
    base = f"/api/workspaces/{ws['wid']}"

    in_lorca = create_manual(bea, ws, *TIMES, project_id=ws["lorca"])
    manual_cervantes = bea.post(
        f"{base}/entries",
        json={**task(ws, project_id=ws["cervantes"]), "start_at": TIMES[0], "end_at": TIMES[1]},
    )
    timer_cervantes = bea.post(f"{base}/timer/start", json=task(ws, project_id=ws["cervantes"]))
    list_cervantes = bea.get(f"{base}/entries", params={"project_id": ws["cervantes"]})

    assert in_lorca["project_id"] == ws["lorca"]
    assert manual_cervantes.status_code == 422
    assert timer_cervantes.status_code == 422
    assert list_cervantes.status_code == 404


def test_no_puede_mover_una_tarea_a_otro_proyecto(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    accept(bea, invite(ana, ws["wid"], ws["lorca"]))
    entry = create_manual(bea, ws, *TIMES, project_id=ws["lorca"])

    response = bea.patch(f"/api/entries/{entry['id']}", json={"project_id": ws["cervantes"]})

    assert response.status_code == 422


def test_invitacion_al_espacio_da_todos_los_proyectos(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")

    join(ana, bea, ws["wid"])

    assert visible_projects(bea, ws["wid"]) == ["Cervantes", "Lorca"]


def test_otra_invitacion_a_proyecto_suma_ese_proyecto(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    accept(bea, invite(ana, ws["wid"], ws["lorca"]))

    accept(bea, invite(ana, ws["wid"], ws["cervantes"]))
    create_project(ana, ws["wid"], "Quijote")

    assert visible_projects(bea, ws["wid"]) == ["Cervantes", "Lorca"]


def test_invitacion_al_espacio_amplia_a_un_miembro_limitado(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    accept(bea, invite(ana, ws["wid"], ws["lorca"]))

    accept(bea, invite(ana, ws["wid"]))

    assert visible_projects(bea, ws["wid"]) == ["Cervantes", "Lorca"]


def test_link_que_no_da_nada_nuevo_no_gasta_uso(make_client):
    ana, ws = company(make_client)
    bea, cris = make_client("bea"), make_client("cris")
    join(ana, bea, ws["wid"])  # Bea ya lo ve todo
    token = invite(ana, ws["wid"], ws["lorca"])
    accept(cris, token)  # Cris entra a Lorca: 1 uso

    assert accept(bea, token).status_code == 200
    assert accept(cris, token).status_code == 200
    assert invitation_uses(ana, ws["wid"])[0] == 1


def test_miembros_muestran_su_acceso(make_client):
    ana, ws = company(make_client)
    bea, cris = make_client("bea"), make_client("cris")
    accept(bea, invite(ana, ws["wid"], ws["lorca"]))
    join(ana, cris, ws["wid"])

    members = {m["name"]: m for m in ana.get(f"/api/workspaces/{ws['wid']}/members").json()}

    assert members["Ana"]["all_projects"] is True
    assert (members["Bea"]["all_projects"], members["Bea"]["project_ids"]) == (False, [ws["lorca"]])
    assert members["Cris"]["all_projects"] is True


# --- El dueño cambia el acceso ---


def test_cambiar_el_acceso_de_un_miembro(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    join(ana, bea, ws["wid"])
    url = f"/api/workspaces/{ws['wid']}/members/{user_id(bea)}/access"

    limited = ana.put(url, json={"all_projects": False, "project_ids": [ws["cervantes"]]})
    only_cervantes = visible_projects(bea, ws["wid"])
    full = ana.put(url, json={"all_projects": True})

    assert limited.status_code == 204
    assert only_cervantes == ["Cervantes"]
    assert full.status_code == 204
    assert visible_projects(bea, ws["wid"]) == ["Cervantes", "Lorca"]


def test_quitar_acceso_mantiene_sus_horas_en_el_panel(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    join(ana, bea, ws["wid"])
    entry = create_manual(bea, ws, *TIMES, project_id=ws["lorca"])

    ana.put(
        f"/api/workspaces/{ws['wid']}/members/{user_id(bea)}/access",
        json={"all_projects": False, "project_ids": [ws["cervantes"]]},
    )
    summary = ana.get(
        f"/api/workspaces/{ws['wid']}/reports/summary", params={"period": "2026-10-A"}
    ).json()

    assert summary["total_seconds"] == 3600
    assert bea.get(f"/api/workspaces/{ws['wid']}/entries").json() == []
    assert bea.patch(f"/api/entries/{entry['id']}", json={"title": "X"}).status_code == 404


def test_acceso_con_proyecto_ajeno_o_por_quien_no_es_dueno(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    join(ana, bea, ws["wid"])
    other = setup_workspace(ana)
    url = f"/api/workspaces/{ws['wid']}/members/{user_id(bea)}/access"

    foreign = ana.put(url, json={"all_projects": False, "project_ids": [other["project"]]})
    by_member = bea.put(url, json={"all_projects": True})
    owner_target = ana.put(
        f"/api/workspaces/{ws['wid']}/members/{user_id(ana)}/access", json={"all_projects": False}
    )

    assert foreign.status_code == 422
    assert by_member.status_code == 403
    assert owner_target.status_code == 409


def test_expulsado_vuelve_solo_con_lo_que_diga_el_link(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    accept(bea, invite(ana, ws["wid"], ws["lorca"]))
    accept(bea, invite(ana, ws["wid"], ws["cervantes"]))
    ana.delete(f"/api/workspaces/{ws['wid']}/members/{user_id(bea)}")

    accept(bea, invite(ana, ws["wid"], ws["lorca"]))

    assert visible_projects(bea, ws["wid"]) == ["Lorca"]


def test_transferir_a_un_miembro_limitado_le_da_todo(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    accept(bea, invite(ana, ws["wid"], ws["lorca"]))

    ana.patch(f"/api/workspaces/{ws['wid']}", json={"owner_id": user_id(bea)})

    assert visible_projects(bea, ws["wid"]) == ["Cervantes", "Lorca"]


# --- Links a proyectos archivados o ajenos ---


def test_proyecto_archivado_invalida_su_link(make_client):
    ana, ws = company(make_client)
    token = invite(ana, ws["wid"], ws["lorca"])

    ana.patch(f"/api/workspaces/{ws['wid']}/projects/{ws['lorca']}", json={"archived": True})

    assert make_client().get(f"/api/invitations/{token}").json()["status"] == "archived"
    assert accept(make_client("bea"), token).status_code == 410
    archived = ana.post(
        f"/api/workspaces/{ws['wid']}/invitations", json={"project_id": ws["lorca"]}
    )
    assert archived.status_code == 409


def test_no_se_invita_a_un_proyecto_de_otro_espacio(make_client):
    ana, ws = company(make_client)
    other = setup_workspace(ana)

    response = ana.post(
        f"/api/workspaces/{ws['wid']}/invitations", json={"project_id": other["project"]}
    )

    assert response.status_code == 422


# --- Borrar proyectos y espacios ---


def test_borrar_proyecto_sin_horas(make_client):
    ana, ws = company(make_client)
    token = invite(ana, ws["wid"], ws["cervantes"])

    response = ana.delete(f"/api/workspaces/{ws['wid']}/projects/{ws['cervantes']}")

    assert response.status_code == 204
    assert visible_projects(ana, ws["wid"]) == ["Lorca"]
    # Sus invitaciones se borran con él.
    assert make_client().get(f"/api/invitations/{token}").status_code == 404


def test_proyecto_con_horas_no_se_borra(make_client):
    ana, ws = company(make_client)
    create_manual(ana, ws, *TIMES, project_id=ws["lorca"])

    response = ana.delete(f"/api/workspaces/{ws['wid']}/projects/{ws['lorca']}")

    assert response.status_code == 409
    assert "archívalo" in response.json()["detail"]


def test_solo_el_dueno_borra_proyectos(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    join(ana, bea, ws["wid"])

    assert bea.delete(f"/api/workspaces/{ws['wid']}/projects/{ws['lorca']}").status_code == 403


def test_borrar_espacio_sin_horas_con_todo_lo_suyo(make_client):
    ana, ws = company(make_client)
    bea = make_client("bea")
    accept(bea, invite(ana, ws["wid"], ws["lorca"]))
    token = invite(ana, ws["wid"])

    response = ana.delete(f"/api/workspaces/{ws['wid']}")

    assert response.status_code == 204
    assert ana.get("/api/workspaces").json() == []
    assert bea.get("/api/workspaces").json() == []
    assert ana.get(f"/api/workspaces/{ws['wid']}/members").status_code == 404
    assert make_client().get(f"/api/invitations/{token}").status_code == 404


def test_espacio_con_horas_no_se_borra(make_client):
    ana, ws = company(make_client)
    create_manual(ana, ws, *TIMES)

    assert ana.delete(f"/api/workspaces/{ws['wid']}").status_code == 409


def test_borrar_espacio_solo_el_dueno(make_client):
    ana, ws = company(make_client)
    bea, intruso = make_client("bea"), make_client("intruso")
    join(ana, bea, ws["wid"])

    assert bea.delete(f"/api/workspaces/{ws['wid']}").status_code == 403
    assert intruso.delete(f"/api/workspaces/{ws['wid']}").status_code == 404
