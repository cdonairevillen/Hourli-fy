"""Importar PDFs de Clockify (rutas del dueño), usuarios fantasma y links para reclamarlos."""

import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Category, Subcategory, TimeEntry, User
from tests.test_clockify_pdf import FakeEntry, build_clockify_pdf
from tests.test_workspaces import create_workspace, join, user_id


def entry(user: str, day: str, start: str, end: str, duration: str, **changes) -> FakeEntry:
    values = dict(
        day=day,
        user=user,
        start=start,
        end=end,
        duration=duration,
        description=["Composición"],
        project=["Scripts & scores - Banda sonora - Jaleo"],
    )
    return FakeEntry(**(values | changes))


# Dos personas; diciembre es horario de invierno (UTC+1).
BASIC = [
    entry("Bea Ruiz", "02/12/2024", "10:00:00", "12:00:00", "02:00:00"),
    entry("Irene Félix", "02/12/2024", "10:00:00", "11:00:00", "01:00:00", project=["Reuniones"]),
    entry("Irene Félix", "03/12/2024", "23:00:00", "01:00:00", "02:00:00", plus_days=1),
]
BASIC_TOTAL = "5:00:00"


def upload(pdf: bytes) -> dict:
    return {"file": ("informe.pdf", pdf, "application/pdf")}


def preview(client: TestClient, wid: str, pdf: bytes):
    return client.post(f"/api/workspaces/{wid}/imports/preview", files=upload(pdf))


def do_import(client: TestClient, wid: str, pdf: bytes, **options):
    options.setdefault("project_name", "Proyecto Lorca")
    return client.post(
        f"/api/workspaces/{wid}/imports", files=upload(pdf), data={"options": json.dumps(options)}
    )


def members_by_name(client: TestClient, wid: str) -> dict:
    return {m["name"]: m for m in client.get(f"/api/workspaces/{wid}/members").json()}


def test_vista_previa_sugiere_personas_y_labels_sin_guardar_nada(make_client, db: Session):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)
    pdf = build_clockify_pdf(BASIC, total=BASIC_TOTAL)

    response = preview(ana, wid, pdf)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_seconds"] == 5 * 3600
    assert data["entry_count"] == 3
    people = {p["name"]: p for p in data["people"]}
    # "Bea Ruiz" no coincide con "Bea"; el email bea@... tampoco empieza por "bea ruiz".
    assert people["Bea Ruiz"]["user_id"] is None
    assert people["Irene Félix"]["total_seconds"] == 3 * 3600
    labels = {label["project_line"]: label for label in data["labels"]}
    jaleo = labels["Scripts & scores - Banda sonora - Jaleo"]
    assert (jaleo["label"], jaleo["sublabel"]) == ("Scripts & scores", "Banda sonora - Jaleo")
    assert labels["Reuniones"]["sublabel"] is None
    assert db.exec(select(TimeEntry)).all() == []


def test_vista_previa_reconoce_el_nombre_de_usuario_de_clockify_por_el_email(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)
    # Clockify enseña el inicio del email a quien no puso nombre: "bea" → bea@example.com.
    rows = [entry("bea", "02/12/2024", "10:00:00", "11:00:00", "01:00:00")]
    pdf = build_clockify_pdf(rows, total="1:00:00")

    [person] = preview(ana, wid, pdf).json()["people"]

    assert person["user_id"] == user_id(bea)
    assert person["is_ghost"] is False


def test_importar_crea_fantasmas_labels_y_registros_en_utc(make_client, db: Session):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    pdf = build_clockify_pdf(BASIC, total=BASIC_TOTAL)

    response = do_import(ana, wid, pdf)

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["created_count"] == 3
    assert result["imported_seconds"] == 5 * 3600
    assert sorted(result["ghosts_created"]) == ["Bea Ruiz", "Irene Félix"]
    members = members_by_name(ana, wid)
    assert members["Irene Félix"]["is_ghost"] is True
    assert members["Irene Félix"]["email"].endswith("@hourlify.invalid")
    # El fantasma solo ve el proyecto donde tiene horas.
    assert members["Irene Félix"]["project_ids"] == [result["project_id"]]

    irene = db.exec(select(User).where(User.name == "Irene Félix")).one()
    entries = db.exec(
        select(TimeEntry).where(TimeEntry.user_id == irene.id).order_by(TimeEntry.start_at)
    ).all()
    # 23:00 en Madrid (UTC+1) = 22:00 UTC; acaba al día siguiente.
    assert entries[1].start_at == datetime(2024, 12, 3, 22, 0, tzinfo=UTC)
    assert entries[1].end_at == datetime(2024, 12, 4, 0, 0, tzinfo=UTC)
    category = db.get(Category, entries[1].category_id)
    subcategory = db.get(Subcategory, entries[1].subcategory_id)
    assert (category.name, subcategory.name) == ("Scripts & scores", "Banda sonora - Jaleo")
    assert entries[0].subcategory_id is None  # "Reuniones": label sin sublabel


def test_reimportar_no_duplica_ni_crea_otro_fantasma(make_client, db: Session):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    pdf = build_clockify_pdf(BASIC, total=BASIC_TOTAL)
    do_import(ana, wid, pdf)

    again = do_import(ana, wid, pdf).json()

    assert again["created_count"] == 0
    assert again["duplicate_count"] == 3
    assert again["ghosts_created"] == []
    assert len(db.exec(select(TimeEntry)).all()) == 3
    assert preview(ana, wid, pdf).json()["duplicate_count"] == 3


def test_solapes_se_mueven_detras_y_las_de_mas_de_24h_se_parten(make_client, db: Session):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    rows = [
        entry("Irene", "02/12/2024", "10:00:00", "12:00:00", "02:00:00"),
        # Se solapa con la anterior: irá de 12:00 a 13:00 (misma duración).
        entry("Irene", "02/12/2024", "11:00:00", "12:00:00", "01:00:00", description=["Otra"]),
        # 30 horas: dos registros (24 h + 6 h) seguidos.
        entry("Irene", "05/12/2024", "08:00:00", "14:00:00", "30:00:00", plus_days=1),
        # 0 segundos: no se guarda.
        entry("Irene", "07/12/2024", "08:00:00", "08:00:00", "00:00:00"),
    ]
    pdf = build_clockify_pdf(rows, total="33:00:00")

    result = do_import(ana, wid, pdf).json()

    assert result["shifted_count"] == 1
    assert result["split_count"] == 1
    assert result["empty_count"] == 1
    assert result["imported_seconds"] == 33 * 3600
    stored = db.exec(select(TimeEntry).order_by(TimeEntry.start_at)).all()
    assert [(e.start_at.hour, e.end_at.hour) for e in stored[:2]] == [(9, 11), (11, 12)]
    assert sum((e.end_at - e.start_at).total_seconds() for e in stored) == 33 * 3600
    assert len(stored) == 4


def test_asignar_una_persona_a_un_miembro(make_client, db: Session):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)
    pdf = build_clockify_pdf(BASIC, total=BASIC_TOTAL)

    result = do_import(ana, wid, pdf, people=[{"name": "Bea Ruiz", "user_id": user_id(bea)}]).json()

    assert result["ghosts_created"] == ["Irene Félix"]
    [mine] = db.exec(select(TimeEntry).where(TimeEntry.user_id == user_id(bea))).all()
    assert mine.title == "Composición"


def test_asignar_a_quien_no_es_miembro_da_422_y_no_guarda_nada(make_client, db: Session):
    ana, bea = make_client("ana"), make_client("bea")
    wid = create_workspace(ana)["id"]
    pdf = build_clockify_pdf(BASIC, total=BASIC_TOTAL)

    response = do_import(ana, wid, pdf, people=[{"name": "Bea Ruiz", "user_id": user_id(bea)}])

    assert response.status_code == 422
    assert db.exec(select(TimeEntry)).all() == []


def test_pdf_que_no_cuadra_o_no_es_de_clockify_da_422(make_client, db: Session):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]

    wrong_total = do_import(ana, wid, build_clockify_pdf(BASIC, total="9:00:00"))
    not_pdf = preview(ana, wid, b"no soy un pdf")

    assert wrong_total.status_code == 422
    assert not_pdf.status_code == 422
    assert db.exec(select(TimeEntry)).all() == []


def test_solo_el_dueno_importa(make_client):
    ana, bea, eva = make_client("ana"), make_client("bea"), make_client("eva")
    wid = create_workspace(ana)["id"]
    join(ana, bea, wid)
    pdf = build_clockify_pdf(BASIC, total=BASIC_TOTAL)

    assert preview(bea, wid, pdf).status_code == 403
    assert do_import(bea, wid, pdf).status_code == 403
    assert preview(eva, wid, pdf).status_code == 404


def test_opciones_mal_formadas_dan_422(make_client):
    ana = make_client("ana")
    wid = create_workspace(ana)["id"]
    pdf = build_clockify_pdf(BASIC, total=BASIC_TOTAL)

    response = ana.post(
        f"/api/workspaces/{wid}/imports", files=upload(pdf), data={"options": "{no es json"}
    )

    assert response.status_code == 422


# --- Fantasmas: reclamar sus horas ---


def import_ghosts(ana: TestClient) -> tuple[str, dict]:
    wid = create_workspace(ana)["id"]
    do_import(ana, wid, build_clockify_pdf(BASIC, total=BASIC_TOTAL))
    return wid, members_by_name(ana, wid)


def claim_link(client: TestClient, wid: str, uid: str):
    return client.post(f"/api/workspaces/{wid}/members/{uid}/claim-link")


def test_reclamar_un_fantasma_pasa_sus_horas_y_su_acceso(make_client, db: Session):
    ana, irene = make_client("ana"), make_client("irene")
    wid, members = import_ghosts(ana)
    ghost_id = members["Irene Félix"]["user_id"]
    link = claim_link(ana, wid, ghost_id)
    assert link.status_code == 201, link.text
    token = link.json()["token"]

    shown = make_client().get(f"/api/invitations/{token}").json()
    accepted = irene.post(f"/api/invitations/{token}/accept")

    assert shown["claim_user_name"] == "Irene Félix"
    assert accepted.status_code == 200, accepted.text
    entries = db.exec(select(TimeEntry).where(TimeEntry.user_id == user_id(irene))).all()
    assert len(entries) == 2
    after = members_by_name(ana, wid)
    assert "Irene Félix" not in after
    assert after["Irene"]["all_projects"] is False
    assert after["Irene"]["project_ids"] == members["Irene Félix"]["project_ids"]
    listed = ana.get(f"/api/workspaces/{wid}/invitations").json()
    assert listed[0]["claim_user_name"] == "Irene Félix"
    # Un solo uso: el link ya no vale.
    assert make_client("otra").post(f"/api/invitations/{token}/accept").status_code == 410


def test_reclamar_con_solapes_no_mueve_nada(make_client, db: Session):
    ana, irene = make_client("ana"), make_client("irene")
    wid, members = import_ghosts(ana)
    join(ana, irene, wid)
    project_id = members["Irene Félix"]["project_ids"][0]
    category_id = db.exec(select(Category.id).where(Category.name == "Reuniones")).one()
    # Irene ya tiene una tarea a la misma hora que una del fantasma (10:00 Madrid = 09:00 UTC).
    own = irene.post(
        f"/api/workspaces/{wid}/entries",
        json={
            "project_id": str(project_id),
            "category_id": str(category_id),
            "title": "Mía",
            "start_at": "2024-12-02T09:30:00Z",
            "end_at": "2024-12-02T10:30:00Z",
        },
    )
    assert own.status_code == 201, own.text
    token = claim_link(ana, wid, members["Irene Félix"]["user_id"]).json()["token"]

    response = irene.post(f"/api/invitations/{token}/accept")

    assert response.status_code == 409
    ghost = db.get(User, members["Irene Félix"]["user_id"])
    assert len(db.exec(select(TimeEntry).where(TimeEntry.user_id == ghost.id)).all()) == 2


def test_link_para_reclamar_solo_de_fantasmas_y_solo_el_dueno(make_client):
    ana, bea = make_client("ana"), make_client("bea")
    wid, members = import_ghosts(ana)
    join(ana, bea, wid)

    assert claim_link(ana, wid, user_id(bea)).status_code == 409
    assert claim_link(bea, wid, members["Bea Ruiz"]["user_id"]).status_code == 403
    assert claim_link(ana, wid, user_id(ana)).status_code == 409


def test_un_fantasma_no_puede_ser_dueno(make_client):
    ana = make_client("ana")
    wid, members = import_ghosts(ana)

    ghost_id = members["Bea Ruiz"]["user_id"]

    response = ana.patch(f"/api/workspaces/{wid}", json={"owner_id": ghost_id})

    assert response.status_code == 422
