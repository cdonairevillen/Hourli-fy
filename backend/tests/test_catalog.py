from fastapi.testclient import TestClient

from tests.test_workspaces import create_workspace, join


def create_project(client: TestClient, wid: str, name: str = "Película", **body) -> dict:
    response = client.post(f"/api/workspaces/{wid}/projects", json={"name": name, **body})
    assert response.status_code == 201, response.text
    return response.json()


def create_category(client: TestClient, wid: str, name: str = "Acto 1") -> dict:
    response = client.post(f"/api/workspaces/{wid}/categories", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def create_subcategory(client: TestClient, wid: str, cid: str, name: str = "Personajes 3D") -> dict:
    response = client.post(
        f"/api/workspaces/{wid}/categories/{cid}/subcategories", json={"name": name}
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- Proyectos ---


def test_crear_y_listar_proyectos(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]

    project = create_project(ana, wid, "  Película Pepe  ", color="#FF0000")

    assert project["name"] == "Película Pepe"
    assert project["color"] == "#FF0000"
    assert [p["name"] for p in ana.get(f"/api/workspaces/{wid}/projects").json()] == [
        "Película Pepe"
    ]


def test_proyecto_sin_color_usa_el_de_por_defecto(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]

    assert create_project(ana, wid)["color"].startswith("#")


def test_color_invalido_da_422(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]

    response = ana.post(f"/api/workspaces/{wid}/projects", json={"name": "X", "color": "rojo"})

    assert response.status_code == 422


def test_nombre_en_blanco_da_422(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]

    assert ana.post(f"/api/workspaces/{wid}/projects", json={"name": "   "}).status_code == 422


def test_proyecto_duplicado_da_409_aunque_este_archivado(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    project = create_project(ana, wid, "Película")
    ana.patch(f"/api/workspaces/{wid}/projects/{project['id']}", json={"archived": True})

    response = ana.post(f"/api/workspaces/{wid}/projects", json={"name": "Película"})

    assert response.status_code == 409


def test_mismo_nombre_en_otro_espacio_si_se_puede(make_client):
    ana = make_client("ana")
    first = create_workspace(ana, "Uno")["id"]
    second = create_workspace(ana, "Dos")["id"]
    create_project(ana, first, "Película")

    create_project(ana, second, "Película")


def test_editar_proyecto(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    project = create_project(ana, wid)

    response = ana.patch(
        f"/api/workspaces/{wid}/projects/{project['id']}",
        json={"name": "Otro nombre", "color": "#00ff00"},
    )

    assert response.status_code == 200
    assert (response.json()["name"], response.json()["color"]) == ("Otro nombre", "#00ff00")


def test_renombrar_a_un_nombre_existente_da_409(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    create_project(ana, wid, "A")
    project_b = create_project(ana, wid, "B")

    response = ana.patch(f"/api/workspaces/{wid}/projects/{project_b['id']}", json={"name": "A"})

    assert response.status_code == 409


def test_archivados_solo_salen_si_se_piden(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    project = create_project(ana, wid)
    ana.patch(f"/api/workspaces/{wid}/projects/{project['id']}", json={"archived": True})

    assert ana.get(f"/api/workspaces/{wid}/projects").json() == []
    archived = ana.get(f"/api/workspaces/{wid}/projects?include_archived=true").json()
    assert [p["archived"] for p in archived] == [True]


# --- Labels y sublabels ---


def test_labels_con_sus_sublabels(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    acto = create_category(ana, wid, "Acto 1")
    create_category(ana, wid, "Gestión")
    create_subcategory(ana, wid, acto["id"], "Entornos 3D")
    create_subcategory(ana, wid, acto["id"], "Personajes")

    labels = ana.get(f"/api/workspaces/{wid}/categories").json()

    assert [(c["name"], [s["name"] for s in c["subcategories"]]) for c in labels] == [
        ("Acto 1", ["Entornos 3D", "Personajes"]),
        ("Gestión", []),
    ]


def test_label_duplicada_da_409(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    create_category(ana, wid, "Acto 1")

    response = ana.post(f"/api/workspaces/{wid}/categories", json={"name": "Acto 1"})

    assert response.status_code == 409


def test_misma_sublabel_en_labels_distintas_si_se_puede(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    acto1 = create_category(ana, wid, "Acto 1")
    acto2 = create_category(ana, wid, "Acto 2")
    create_subcategory(ana, wid, acto1["id"], "Personajes")

    create_subcategory(ana, wid, acto2["id"], "Personajes")
    response = ana.post(
        f"/api/workspaces/{wid}/categories/{acto1['id']}/subcategories",
        json={"name": "Personajes"},
    )

    assert response.status_code == 409


def test_archivar_label_la_oculta_con_sus_sublabels(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    acto = create_category(ana, wid)
    create_subcategory(ana, wid, acto["id"])

    response = ana.patch(f"/api/workspaces/{wid}/categories/{acto['id']}", json={"archived": True})

    assert response.json()["archived"] is True
    assert len(response.json()["subcategories"]) == 1
    assert ana.get(f"/api/workspaces/{wid}/categories").json() == []
    assert len(ana.get(f"/api/workspaces/{wid}/categories?include_archived=true").json()) == 1


def test_renombrar_y_archivar_sublabel(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    acto = create_category(ana, wid)
    sub = create_subcategory(ana, wid, acto["id"], "Personajes")
    url = f"/api/workspaces/{wid}/categories/{acto['id']}/subcategories/{sub['id']}"

    assert ana.patch(url, json={"name": "Personajes 3D"}).json()["name"] == "Personajes 3D"
    assert ana.patch(url, json={"archived": True}).json()["archived"] is True
    assert ana.get(f"/api/workspaces/{wid}/categories").json()[0]["subcategories"] == []


def test_sublabel_por_una_label_que_no_es_la_suya_da_404(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    acto1 = create_category(ana, wid, "Acto 1")
    acto2 = create_category(ana, wid, "Acto 2")
    sub = create_subcategory(ana, wid, acto1["id"])

    response = ana.patch(
        f"/api/workspaces/{wid}/categories/{acto2['id']}/subcategories/{sub['id']}",
        json={"name": "X"},
    )

    assert response.status_code == 404


# --- Permisos y aislamiento ---


def test_miembro_lee_pero_no_escribe(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)
    project = create_project(ana, wid)
    acto = create_category(ana, wid)
    sub = create_subcategory(ana, wid, acto["id"])

    assert len(bea.get(f"/api/workspaces/{wid}/projects").json()) == 1
    assert len(bea.get(f"/api/workspaces/{wid}/categories").json()) == 1
    base = f"/api/workspaces/{wid}"
    assert bea.post(f"{base}/projects", json={"name": "X"}).status_code == 403
    assert bea.patch(f"{base}/projects/{project['id']}", json={"name": "X"}).status_code == 403
    assert bea.post(f"{base}/categories", json={"name": "X"}).status_code == 403
    assert bea.patch(f"{base}/categories/{acto['id']}", json={"name": "X"}).status_code == 403
    sub_base = f"{base}/categories/{acto['id']}/subcategories"
    assert bea.post(sub_base, json={"name": "X"}).status_code == 403
    assert bea.patch(f"{sub_base}/{sub['id']}", json={"name": "X"}).status_code == 403


def test_ajeno_no_ve_ni_toca_el_catalogo(make_client):
    ana, intruso = make_client("ana"), make_client("intruso")
    wid = create_workspace(ana)["id"]
    project = create_project(ana, wid)
    acto = create_category(ana, wid)
    base = f"/api/workspaces/{wid}"

    assert intruso.get(f"{base}/projects").status_code == 404
    assert intruso.get(f"{base}/categories").status_code == 404
    assert intruso.post(f"{base}/projects", json={"name": "X"}).status_code == 404
    assert intruso.patch(f"{base}/projects/{project['id']}", json={"name": "X"}).status_code == 404
    assert intruso.patch(f"{base}/categories/{acto['id']}", json={"name": "X"}).status_code == 404
    subs = f"{base}/categories/{acto['id']}/subcategories"
    assert intruso.post(subs, json={"name": "X"}).status_code == 404


def test_ids_de_otro_espacio_dan_404(make_client):
    """Ser dueña de dos espacios no permite tocar el catálogo de uno desde la ruta del otro."""
    ana = make_client("ana")
    first = create_workspace(ana, "Uno")["id"]
    second = create_workspace(ana, "Dos")["id"]
    project = create_project(ana, first)
    acto = create_category(ana, first)
    base = f"/api/workspaces/{second}"

    assert ana.patch(f"{base}/projects/{project['id']}", json={"name": "X"}).status_code == 404
    assert ana.patch(f"{base}/categories/{acto['id']}", json={"name": "X"}).status_code == 404
    subs = f"{base}/categories/{acto['id']}/subcategories"
    assert ana.post(subs, json={"name": "X"}).status_code == 404


def test_espacio_archivado_se_lee_pero_no_se_modifica(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    project = create_project(ana, wid)
    ana.patch(f"/api/workspaces/{wid}", json={"archived": True})
    base = f"/api/workspaces/{wid}"

    assert len(ana.get(f"{base}/projects").json()) == 1
    assert ana.post(f"{base}/projects", json={"name": "X"}).status_code == 409
    assert ana.patch(f"{base}/projects/{project['id']}", json={"name": "X"}).status_code == 409
    assert ana.post(f"{base}/categories", json={"name": "X"}).status_code == 409
