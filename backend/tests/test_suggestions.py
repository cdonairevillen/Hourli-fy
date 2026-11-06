"""Autocompletar al escribir una tarea: GET /workspaces/{wid}/entries/suggestions."""

from fastapi.testclient import TestClient

from tests.test_catalog import create_project
from tests.test_entries import create_manual, setup_workspace
from tests.test_workspaces import join, user_id


def suggestions(client: TestClient, ws: dict, **params) -> list[dict]:
    params.setdefault("project_id", ws["project"])
    response = client.get(f"/api/workspaces/{ws['wid']}/entries/suggestions", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_mis_tareas_sin_repetir_y_las_recientes_primero(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z", title="Animar a Pepe")
    create_manual(ana, ws, "2026-10-06T08:00:00Z", "2026-10-06T09:00:00Z", title="Reunión")
    # Mismo título más tarde (con otras mayúsculas y otra label): una sola sugerencia, la última.
    create_manual(
        ana,
        ws,
        "2026-10-07T08:00:00Z",
        "2026-10-07T09:00:00Z",
        title="animar a pepe",
        category_id=ws["gestion"],
        subcategory_id=None,
    )

    data = suggestions(ana, ws)

    assert [s["title"] for s in data] == ["animar a pepe", "Reunión"]
    assert data[0]["category_id"] == ws["gestion"]
    assert data[0]["subcategory_id"] is None
    assert data[1]["category_id"] == ws["acto"]
    assert data[1]["subcategory_id"] == ws["personajes"]


def test_solo_las_mias_y_de_ese_proyecto(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    ws = setup_workspace(ana)
    join(ana, bea, ws["wid"])
    other = create_project(ana, ws["wid"], "Anuncio")["id"]
    create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z", title="De Ana")
    create_manual(bea, ws, "2026-10-05T08:00:00Z", "2026-10-05T09:00:00Z", title="De Bea")
    create_manual(
        ana, ws, "2026-10-06T08:00:00Z", "2026-10-06T09:00:00Z", project_id=other, title="Spot"
    )

    assert [s["title"] for s in suggestions(ana, ws)] == ["De Ana"]
    assert [s["title"] for s in suggestions(bea, ws)] == ["De Bea"]
    assert [s["title"] for s in suggestions(ana, ws, project_id=other)] == ["Spot"]


def test_filtro_por_texto_y_limite(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    for day, title in [(5, "Animar a Pepe"), (6, "Animar a Juan"), (7, "Revisar 100%")]:
        create_manual(
            ana, ws, f"2026-10-0{day}T08:00:00Z", f"2026-10-0{day}T09:00:00Z", title=title
        )

    assert [s["title"] for s in suggestions(ana, ws, q="ANIMAR")] == [
        "Animar a Juan",
        "Animar a Pepe",
    ]
    # "%" se busca literalmente, no como comodín.
    assert [s["title"] for s in suggestions(ana, ws, q="%")] == ["Revisar 100%"]
    assert len(suggestions(ana, ws, limit=1)) == 1


def test_proyecto_sin_acceso_o_espacio_ajeno_da_404(make_client):
    ana, bea, intruso = make_client("ana"), make_client("bea"), make_client("intruso")
    ws = setup_workspace(ana)
    join(ana, bea, ws["wid"])
    other = create_project(ana, ws["wid"], "Anuncio")["id"]
    ana.put(
        f"/api/workspaces/{ws['wid']}/members/{user_id(bea)}/access",
        json={"all_projects": False, "project_ids": [other]},
    )
    url = f"/api/workspaces/{ws['wid']}/entries/suggestions"

    assert bea.get(url, params={"project_id": ws["project"]}).status_code == 404
    assert bea.get(url, params={"project_id": other}).status_code == 200
    assert intruso.get(url, params={"project_id": ws["project"]}).status_code == 404
    assert ana.get(url).status_code == 422  # project_id es obligatorio
