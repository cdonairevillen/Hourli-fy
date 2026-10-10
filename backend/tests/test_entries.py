from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import TimeEntry
from app.models.common import utc_now
from tests.test_catalog import create_category, create_project, create_subcategory
from tests.test_workspaces import create_workspace, join


def setup_workspace(client: TestClient) -> dict:
    """Espacio con un proyecto, la label "Acto 1" con la sublabel "Personajes" y "Gestión"."""
    wid = create_workspace(client)["id"]
    project = create_project(client, wid, "Película")
    acto = create_category(client, wid, "Acto 1")
    personajes = create_subcategory(client, wid, acto["id"], "Personajes")
    gestion = create_category(client, wid, "Gestión")
    return {
        "wid": wid,
        "project": project["id"],
        "acto": acto["id"],
        "personajes": personajes["id"],
        "gestion": gestion["id"],
    }


def task(ws: dict, **overrides) -> dict:
    body = {
        "project_id": ws["project"],
        "category_id": ws["acto"],
        "subcategory_id": ws["personajes"],
        "title": "Animaciones de Pepe y Juan",
    }
    return {**body, **overrides}


def manual(ws: dict, start: str, end: str, **overrides) -> dict:
    return task(ws, start_at=start, end_at=end, **overrides)


def create_manual(client: TestClient, ws: dict, start: str, end: str, **overrides) -> dict:
    response = client.post(
        f"/api/workspaces/{ws['wid']}/entries", json=manual(ws, start, end, **overrides)
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- Registro manual ---


def test_registro_manual(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)

    entry = create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T10:30:00Z")

    assert entry["source"] == "manual"
    assert entry["duration_seconds"] == 9000
    assert entry["title"] == "Animaciones de Pepe y Juan"


def test_sublabel_es_opcional(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)

    entry = create_manual(
        ana,
        ws,
        "2026-10-05T08:00:00Z",
        "2026-10-05T09:00:00Z",
        category_id=ws["gestion"],
        subcategory_id=None,
        title="Reunión de producción",
    )

    assert entry["subcategory_id"] is None


def test_fechas_sin_zona_horaria_dan_422(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)

    response = ana.post(
        f"/api/workspaces/{ws['wid']}/entries",
        json=manual(ws, "2026-10-05T08:00:00", "2026-10-05T09:00:00"),
    )

    assert response.status_code == 422


def test_fin_antes_del_inicio_da_422(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)

    response = ana.post(
        f"/api/workspaces/{ws['wid']}/entries",
        json=manual(ws, "2026-10-05T10:00:00Z", "2026-10-05T09:00:00Z"),
    )

    assert response.status_code == 422


def test_mas_de_24_horas_da_422(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)

    response = ana.post(
        f"/api/workspaces/{ws['wid']}/entries",
        json=manual(ws, "2026-10-05T08:00:00Z", "2026-10-06T08:00:01Z"),
    )

    assert response.status_code == 422


def test_titulo_vacio_da_422(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)

    response = ana.post(
        f"/api/workspaces/{ws['wid']}/entries",
        json=manual(ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z", title="  "),
    )

    assert response.status_code == 422


def test_solape_con_otro_registro_da_409(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T10:00:00Z")

    response = ana.post(
        f"/api/workspaces/{ws['wid']}/entries",
        json=manual(ws, "2026-10-05T09:30:00Z", "2026-10-05T11:00:00Z"),
    )

    assert response.status_code == 409


def test_registros_seguidos_no_se_solapan(make_client):
    """10:00 de fin y 10:00 de inicio no chocan: los rangos son [inicio, fin)."""
    ana = make_client("ana")
    ws = setup_workspace(ana)
    create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T10:00:00Z")

    create_manual(ana, ws, "2026-10-05T10:00:00Z", "2026-10-05T11:00:00Z")


def test_solape_entre_espacios_distintos_tambien_cuenta(make_client):
    """Una persona no puede estar en dos sitios a la vez, aunque sean espacios distintos."""
    ana = make_client("ana")
    ws1 = setup_workspace(ana)
    ws2 = setup_workspace(ana)
    create_manual(ana, ws1, "2026-10-05T08:00:00Z", "2026-10-05T10:00:00Z")

    response = ana.post(
        f"/api/workspaces/{ws2['wid']}/entries",
        json=manual(ws2, "2026-10-05T09:00:00Z", "2026-10-05T09:30:00Z"),
    )

    assert response.status_code == 409


def test_personas_distintas_pueden_coincidir(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    ws = setup_workspace(ana)
    join(ana, bea, ws["wid"])
    create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T10:00:00Z")

    create_manual(bea, ws, "2026-10-05T08:00:00Z", "2026-10-05T10:00:00Z")


def test_catalogo_archivado_o_ajeno_da_422(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    other = setup_workspace(ana)
    ana.patch(f"/api/workspaces/{ws['wid']}/projects/{ws['project']}", json={"archived": True})
    url = f"/api/workspaces/{ws['wid']}/entries"
    times = ("2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")

    assert ana.post(url, json=manual(ws, *times)).status_code == 422
    assert ana.post(url, json=manual(other, *times)).status_code == 422


def test_sublabel_de_otra_label_da_422(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)

    response = ana.post(
        f"/api/workspaces/{ws['wid']}/entries",
        json=manual(ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z", category_id=ws["gestion"]),
    )

    assert response.status_code == 422


# --- Listado ---


def test_listado_por_dias_de_espana(make_client):
    """El 5 de octubre a las 23:30 UTC ya es día 6 en España (UTC+2 en verano)."""
    ana = make_client("ana")
    ws = setup_workspace(ana)
    create_manual(ana, ws, "2026-10-05T10:00:00Z", "2026-10-05T11:00:00Z", title="Día 5")
    create_manual(ana, ws, "2026-10-05T23:30:00Z", "2026-10-06T00:30:00Z", title="Día 6")
    url = f"/api/workspaces/{ws['wid']}/entries"

    day5 = ana.get(url, params={"from": "2026-10-05", "to": "2026-10-05"}).json()
    day6 = ana.get(url, params={"from": "2026-10-06", "to": "2026-10-06"}).json()

    assert [e["title"] for e in day5] == ["Día 5"]
    assert [e["title"] for e in day6] == ["Día 6"]


def test_listado_por_proyecto_y_solo_lo_mio(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    ws = setup_workspace(ana)
    join(ana, bea, ws["wid"])
    other_project = create_project(ana, ws["wid"], "Anuncio")["id"]
    create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z", title="Peli")
    create_manual(
        ana,
        ws,
        "2026-10-05T09:00:00Z",
        "2026-10-05T10:00:00Z",
        project_id=other_project,
        title="Anuncio",
    )
    create_manual(bea, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z", title="De Bea")
    url = f"/api/workspaces/{ws['wid']}/entries"

    assert [e["title"] for e in ana.get(url).json()] == ["Anuncio", "Peli"]
    by_project = ana.get(url, params={"project_id": ws["project"]}).json()
    assert [e["title"] for e in by_project] == ["Peli"]
    assert [e["title"] for e in bea.get(url).json()] == ["De Bea"]


# --- Editar y borrar ---


def test_editar_registro(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    entry = create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")

    response = ana.patch(
        f"/api/entries/{entry['id']}",
        json={"title": "Otro nombre", "end_at": "2026-10-05T09:30:00Z"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Otro nombre"
    assert response.json()["duration_seconds"] == 5400


def test_cambiar_label_quita_la_sublabel_anterior(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    entry = create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")

    response = ana.patch(f"/api/entries/{entry['id']}", json={"category_id": ws["gestion"]})

    assert response.json()["subcategory_id"] is None


def test_quitar_sublabel_con_null(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    entry = create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")

    response = ana.patch(f"/api/entries/{entry['id']}", json={"subcategory_id": None})

    assert response.json()["subcategory_id"] is None


def test_editar_horas_de_un_registro_con_label_archivada(make_client):
    """La label se archivó después: se pueden corregir las horas sin tener que cambiarla."""
    ana = make_client("ana")
    ws = setup_workspace(ana)
    entry = create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")
    ana.patch(f"/api/workspaces/{ws['wid']}/categories/{ws['acto']}", json={"archived": True})

    response = ana.patch(f"/api/entries/{entry['id']}", json={"end_at": "2026-10-05T09:15:00Z"})

    assert response.status_code == 200


def test_editar_a_un_solape_da_409(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")
    second = create_manual(ana, ws, "2026-10-05T10:00:00Z", "2026-10-05T11:00:00Z")

    response = ana.patch(f"/api/entries/{second['id']}", json={"start_at": "2026-10-05T08:30:00Z"})

    assert response.status_code == 409


def test_campos_obligatorios_no_admiten_null(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    entry = create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")

    assert ana.patch(f"/api/entries/{entry['id']}", json={"title": None}).status_code == 422
    assert ana.patch(f"/api/entries/{entry['id']}", json={"end_at": None}).status_code == 422


def test_borrar_registro(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    entry = create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")

    assert ana.delete(f"/api/entries/{entry['id']}").status_code == 204
    assert ana.get(f"/api/workspaces/{ws['wid']}/entries").json() == []


def test_nadie_toca_registros_ajenos(make_client):
    """Ni otro miembro ni el dueño pueden editar o borrar lo que registró otra persona."""
    ana, bea = make_client("ana"), make_client("bea")
    ws = setup_workspace(ana)
    join(ana, bea, ws["wid"])
    entry_bea = create_manual(bea, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")

    assert ana.patch(f"/api/entries/{entry_bea['id']}", json={"title": "X"}).status_code == 404
    assert ana.delete(f"/api/entries/{entry_bea['id']}").status_code == 404


def test_expulsado_no_toca_sus_registros_del_espacio(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    ws = setup_workspace(ana)
    join(ana, bea, ws["wid"])
    entry = create_manual(bea, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")
    bea_id = bea.get("/api/auth/me").json()["id"]
    ana.delete(f"/api/workspaces/{ws['wid']}/members/{bea_id}")

    assert bea.patch(f"/api/entries/{entry['id']}", json={"title": "X"}).status_code == 404
    assert bea.get(f"/api/workspaces/{ws['wid']}/entries").status_code == 404


def test_ajeno_no_registra_en_el_espacio(make_client):
    ana, intruso = make_client("ana"), make_client("intruso")
    ws = setup_workspace(ana)
    url = f"/api/workspaces/{ws['wid']}"
    body = manual(ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")

    assert intruso.post(f"{url}/entries", json=body).status_code == 404
    assert intruso.get(f"{url}/entries").status_code == 404
    assert intruso.post(f"{url}/timer/start", json=task(ws)).status_code == 404


def test_espacio_archivado_no_admite_registros(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    entry = create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z")
    ana.patch(f"/api/workspaces/{ws['wid']}", json={"archived": True})
    url = f"/api/workspaces/{ws['wid']}"

    body = manual(ws, "2026-10-06T08:00:00Z", "2026-10-06T09:00:00Z")
    assert ana.post(f"{url}/entries", json=body).status_code == 409
    assert ana.post(f"{url}/timer/start", json=task(ws)).status_code == 409
    assert ana.patch(f"/api/entries/{entry['id']}", json={"title": "X"}).status_code == 409
    assert len(ana.get(f"{url}/entries").json()) == 1


# --- Cronómetro ---


def test_arrancar_y_parar_cronometro(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)

    started = ana.post(f"/api/workspaces/{ws['wid']}/timer/start", json=task(ws))
    current = ana.get("/api/timer/current").json()
    stopped = ana.post("/api/timer/stop")

    assert started.status_code == 201
    assert started.json()["end_at"] is None
    assert started.json()["duration_seconds"] is None
    assert started.json()["source"] == "timer"
    assert current["id"] == started.json()["id"]
    assert stopped.status_code == 200
    assert stopped.json()["end_at"] is not None
    assert ana.get("/api/timer/current").json() is None


def test_parar_sin_cronometro_da_404(make_client):
    assert make_client("ana").post("/api/timer/stop").status_code == 404


def test_arrancar_otro_para_el_anterior_aunque_sea_de_otro_espacio(make_client, db: Session):
    ana = make_client("ana")
    ws1 = setup_workspace(ana)
    ws2 = setup_workspace(ana)
    first = ana.post(f"/api/workspaces/{ws1['wid']}/timer/start", json=task(ws1)).json()
    # El primero empezó hace una hora (si no, los dos serían del mismo instante).
    db.get(TimeEntry, first["id"]).start_at = utc_now() - timedelta(hours=1)
    db.commit()

    second = ana.post(f"/api/workspaces/{ws2['wid']}/timer/start", json=task(ws2))

    assert second.status_code == 201
    assert ana.get("/api/timer/current").json()["id"] == second.json()["id"]
    running = db.exec(select(TimeEntry).where(TimeEntry.end_at.is_(None))).all()
    assert len(running) == 1
    stopped_first = ana.get(f"/api/workspaces/{ws1['wid']}/entries").json()[0]
    assert stopped_first["duration_seconds"] >= 3600


def test_cronometro_olvidado_se_corta_en_24_horas(make_client, db: Session):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    started = ana.post(f"/api/workspaces/{ws['wid']}/timer/start", json=task(ws)).json()
    db.get(TimeEntry, started["id"]).start_at = utc_now() - timedelta(hours=30)
    db.commit()

    stopped = ana.post("/api/timer/stop").json()

    assert stopped["duration_seconds"] == 24 * 3600


def test_registro_manual_que_pisa_el_cronometro_da_409(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    ana.post(f"/api/workspaces/{ws['wid']}/timer/start", json=task(ws))
    now = utc_now()

    response = ana.post(
        f"/api/workspaces/{ws['wid']}/entries",
        json=manual(
            ws,
            (now - timedelta(minutes=10)).isoformat(),
            (now + timedelta(minutes=10)).isoformat(),
        ),
    )

    assert response.status_code == 409


def test_al_cronometro_en_marcha_no_se_le_pone_fin_editando(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    started = ana.post(f"/api/workspaces/{ws['wid']}/timer/start", json=task(ws)).json()

    response = ana.patch(f"/api/entries/{started['id']}", json={"end_at": utc_now().isoformat()})
    renamed = ana.patch(f"/api/entries/{started['id']}", json={"title": "Otra tarea"})

    assert response.status_code == 422
    assert renamed.status_code == 200


def test_borrar_el_cronometro_en_marcha_lo_descarta(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    started = ana.post(f"/api/workspaces/{ws['wid']}/timer/start", json=task(ws)).json()

    assert ana.delete(f"/api/entries/{started['id']}").status_code == 204
    assert ana.get("/api/timer/current").json() is None


def test_cronometros_de_personas_distintas_son_independientes(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    ws = setup_workspace(ana)
    join(ana, bea, ws["wid"])

    ana.post(f"/api/workspaces/{ws['wid']}/timer/start", json=task(ws))
    bea.post(f"/api/workspaces/{ws['wid']}/timer/start", json=task(ws))

    assert ana.get("/api/timer/current").json() is not None
    assert bea.get("/api/timer/current").json() is not None
    assert ana.get("/api/timer/current").json()["id"] != bea.get("/api/timer/current").json()["id"]
