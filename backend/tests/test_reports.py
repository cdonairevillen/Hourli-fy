from datetime import date

from fastapi.testclient import TestClient

from tests.test_catalog import create_category, create_project
from tests.test_entries import create_manual, setup_workspace, task
from tests.test_workspaces import join, user_id

# Un día del periodo de 14 días del 26-sep al 9-oct de 2026, donde caen las horas de team().
PERIOD = "2026-10-05"


def team(make_client) -> tuple[TestClient, TestClient, dict]:
    """Ana (dueña) y Bea (miembro) con unas horas en el periodo del 26-sep al 9-oct de 2026.

    Ana: 2 h "Personajes" el día 5 + 1 h "Gestión" el día 6.  Bea: 3 h el día 5.
    """
    ana, bea = make_client("ana"), make_client("bea")
    ws = setup_workspace(ana)
    join(ana, bea, ws["wid"])
    create_manual(ana, ws, "2026-10-05T08:00:00Z", "2026-10-05T10:00:00Z", title="Animar a Pepe")
    create_manual(
        ana,
        ws,
        "2026-10-06T08:00:00Z",
        "2026-10-06T09:00:00Z",
        category_id=ws["gestion"],
        subcategory_id=None,
        title="Reunión",
    )
    create_manual(bea, ws, "2026-10-05T08:00:00Z", "2026-10-05T11:00:00Z", title="Animar a Juan")
    return ana, bea, ws


def summary(client: TestClient, ws: dict, **params) -> dict:
    response = client.get(f"/api/workspaces/{ws['wid']}/reports/summary", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def entries(client: TestClient, ws: dict, **params) -> dict:
    response = client.get(f"/api/workspaces/{ws['wid']}/reports/entries", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_resumen_del_periodo(make_client):
    ana, _, ws = team(make_client)

    data = summary(ana, ws, period=PERIOD)

    assert (data["from_date"], data["to_date"]) == ("2026-09-26", "2026-10-09")
    assert data["total_seconds"] == 6 * 3600
    assert data["entry_count"] == 3
    # Empate a 3 h: desempata el nombre.
    assert [(u["name"], u["total_seconds"]) for u in data["by_user"]] == [
        ("Ana", 3 * 3600),
        ("Bea", 3 * 3600),
    ]
    assert [(p["name"], p["total_seconds"]) for p in data["by_project"]] == [("Película", 21600)]
    assert [(c["name"], c["total_seconds"]) for c in data["by_category"]] == [
        ("Acto 1", 5 * 3600),
        ("Gestión", 3600),
    ]
    assert data["by_day"] == [
        {"day": "2026-10-05", "total_seconds": 5 * 3600},
        {"day": "2026-10-06", "total_seconds": 3600},
    ]


def test_periodos_de_14_dias_seguidos(make_client):
    """Bloques de 14 días desde el sábado 7-nov-2026, hacia delante y hacia atrás."""
    ana = make_client("ana")
    ws = setup_workspace(ana)

    def period_of(day: str) -> tuple[str, str]:
        data = summary(ana, ws, period=day)
        return data["from_date"], data["to_date"]

    # Cualquier día del bloque da el mismo bloque.
    assert period_of("2026-11-07") == ("2026-11-07", "2026-11-20")
    assert period_of("2026-11-20") == ("2026-11-07", "2026-11-20")
    assert period_of("2026-11-21") == ("2026-11-21", "2026-12-04")
    # Antes del primer bloque también hay periodos (el historial no se queda sin ellos).
    assert period_of("2026-11-06") == ("2026-10-24", "2026-11-06")
    # Cruzan meses y años sin perder días: el 31 está dentro.
    assert period_of("2026-12-31") == ("2026-12-19", "2027-01-01")


def test_sin_periodo_usa_el_actual(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)

    data = summary(ana, ws)

    start, end = date.fromisoformat(data["from_date"]), date.fromisoformat(data["to_date"])
    assert (end - start).days == 13
    assert (start - date(2026, 11, 7)).days % 14 == 0
    assert start <= date.today() <= end


def test_rango_de_fechas(make_client):
    ana, _, ws = team(make_client)

    data = summary(ana, ws, **{"from": "2026-10-06", "to": "2026-10-06"})

    assert data["total_seconds"] == 3600


def test_periodo_y_rango_a_la_vez_o_mal_escritos_dan_422(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    url = f"/api/workspaces/{ws['wid']}/reports/summary"

    assert ana.get(url, params={"period": PERIOD, "from": "2026-10-01"}).status_code == 422
    # El formato de las quincenas antiguas ya no vale.
    assert ana.get(url, params={"period": "2026-10-A"}).status_code == 422
    assert ana.get(url, params={"period": "2026-13-01"}).status_code == 422
    assert ana.get(url, params={"from": "2026-10-01"}).status_code == 422
    assert ana.get(url, params={"from": "2026-10-10", "to": "2026-10-01"}).status_code == 422


def test_filtro_por_trabajador(make_client):
    ana, bea, ws = team(make_client)

    data = summary(ana, ws, period=PERIOD, user_id=user_id(bea))

    assert data["total_seconds"] == 3 * 3600
    assert [u["name"] for u in data["by_user"]] == ["Bea"]


def test_filtro_por_label_y_sublabel(make_client):
    ana, _, ws = team(make_client)

    by_label = summary(ana, ws, period=PERIOD, category_id=ws["gestion"])
    by_sub = summary(ana, ws, period=PERIOD, subcategory_id=ws["personajes"])

    assert by_label["total_seconds"] == 3600
    assert by_sub["total_seconds"] == 5 * 3600


def test_filtro_por_proyecto(make_client):
    ana, _, ws = team(make_client)
    other = create_project(ana, ws["wid"], "Anuncio")["id"]
    create_manual(
        ana, ws, "2026-10-07T08:00:00Z", "2026-10-07T08:30:00Z", project_id=other, title="Spot"
    )

    data = summary(ana, ws, period=PERIOD, project_id=other)

    assert data["total_seconds"] == 1800


def test_busqueda_en_el_titulo_sin_mayusculas_ni_comodines(make_client):
    ana, _, ws = team(make_client)
    create_manual(ana, ws, "2026-10-07T08:00:00Z", "2026-10-07T08:30:00Z", title="Revisar 100%")

    assert summary(ana, ws, period=PERIOD, q="animar")["entry_count"] == 2
    # "%" se busca literalmente: no es un comodín que lo encuentre todo.
    assert summary(ana, ws, period=PERIOD, q="100%")["entry_count"] == 1
    assert summary(ana, ws, period=PERIOD, q="%")["entry_count"] == 1


def test_el_cronometro_en_marcha_no_cuenta(make_client):
    ana = make_client("ana")
    ws = setup_workspace(ana)
    ana.post(f"/api/workspaces/{ws['wid']}/timer/start", json=task(ws))

    assert summary(ana, ws)["entry_count"] == 0


def test_cuenta_el_dia_de_espana_en_que_empieza(make_client):
    """Empieza el 9-oct (último día de un periodo) a las 23:30 en España (21:30 UTC) y acaba
    ya el 10: cuenta en el periodo del 9, no en el siguiente."""
    ana = make_client("ana")
    ws = setup_workspace(ana)
    create_manual(ana, ws, "2026-10-09T21:30:00Z", "2026-10-09T23:00:00Z")

    assert summary(ana, ws, period="2026-10-09")["entry_count"] == 1
    assert summary(ana, ws, period="2026-10-10")["entry_count"] == 0


def test_las_horas_de_un_expulsado_siguen_contando(make_client):
    ana, bea, ws = team(make_client)
    ana.delete(f"/api/workspaces/{ws['wid']}/members/{user_id(bea)}")

    assert summary(ana, ws, period=PERIOD)["total_seconds"] == 6 * 3600


def test_listado_de_registros_paginado(make_client):
    ana, _, ws = team(make_client)

    first = entries(ana, ws, period=PERIOD, limit=2)
    second = entries(ana, ws, period=PERIOD, limit=2, offset=2)

    assert first["total"] == 3
    # Más reciente primero; Ana y Bea empiezan a la vez el día 5: desempata el nombre.
    assert [e["title"] for e in first["items"]] == ["Reunión", "Animar a Pepe"]
    assert [(e["title"], e["user_name"]) for e in second["items"]] == [("Animar a Juan", "Bea")]


def test_listado_filtrado(make_client):
    ana, bea, ws = team(make_client)

    data = entries(ana, ws, period=PERIOD, user_id=user_id(bea))

    assert [(e["title"], e["user_name"]) for e in data["items"]] == [("Animar a Juan", "Bea")]


def test_solo_el_dueno_ve_el_panel(make_client):
    _, bea, ws = team(make_client)
    base = f"/api/workspaces/{ws['wid']}/reports"

    assert bea.get(f"{base}/summary").status_code == 403
    assert bea.get(f"{base}/entries").status_code == 403


def test_ajeno_no_ve_el_panel(make_client):
    _, _, ws = team(make_client)
    intruso = make_client("intruso")
    base = f"/api/workspaces/{ws['wid']}/reports"

    assert intruso.get(f"{base}/summary").status_code == 404
    assert intruso.get(f"{base}/entries").status_code == 404


def test_no_mezcla_espacios(make_client):
    """Las horas de Ana en otro espacio no aparecen en el panel de este."""
    ana, _, ws = team(make_client)
    other = setup_workspace(ana)
    create_manual(ana, other, "2026-10-08T08:00:00Z", "2026-10-08T12:00:00Z")
    create_category(ana, other["wid"], "Otra")

    assert summary(ana, ws, period=PERIOD)["total_seconds"] == 6 * 3600
    assert summary(ana, other, period=PERIOD)["total_seconds"] == 4 * 3600
