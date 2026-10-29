"""Registros de tiempo (tareas) y cronómetro.

Cada persona solo ve y toca sus propios registros, y solo en los proyectos a los que tiene
acceso. Los totales de todo el espacio son del panel del dueño (fase 4).
"""

import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.deps import CurrentUser, MemberAccess, SessionDep
from app.models import Membership, TimeEntry, User, Workspace
from app.models.common import utc_now
from app.schemas import TimeEntryCreate, TimeEntryRead, TimeEntryUpdate, TimerStart
from app.services.access import accessible_project_ids
from app.services.entries import (
    entry_read,
    find_running,
    local_day_start,
    save_entry,
    stop_entry,
    validate_catalog,
    validate_times,
)

router = APIRouter(tags=["entries"])

CATALOG_FIELDS = {"project_id", "category_id", "subcategory_id"}


def ensure_writable(workspace: Workspace) -> None:
    if workspace.archived:
        raise HTTPException(status.HTTP_409_CONFLICT, "El espacio está archivado")


def get_own_entry(
    session: Session, user: User, entry_id: uuid.UUID
) -> tuple[TimeEntry, set | None]:
    """Un registro mío en un espacio del que sigo siendo miembro y en un proyecto al que sigo
    teniendo acceso; si no, 404 (también si es de otra persona: no se revela que existe).

    Devuelve además los proyectos que puedo usar (None = todos), para validar cambios.
    """
    entry = session.get(TimeEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro no encontrado")
    membership = session.get(Membership, (entry.workspace_id, user.id))
    if membership is None or membership.removed_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro no encontrado")
    workspace = session.get_one(Workspace, entry.workspace_id)
    allowed = accessible_project_ids(session, workspace, membership)
    if allowed is not None and entry.project_id not in allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro no encontrado")
    return entry, allowed


# --- Registros ---


@router.get("/workspaces/{wid}/entries")
def list_my_entries(
    session: SessionDep,
    access: MemberAccess,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    project_id: uuid.UUID | None = None,
) -> list[TimeEntryRead]:
    """Mis registros en el espacio (solo de proyectos a los que tengo acceso), los más recientes
    primero.

    `from` y `to` son días (AAAA-MM-DD, ambos incluidos) en hora de España. Un registro cuenta
    en el día en que empieza, igual que en las quincenas.
    """
    allowed = accessible_project_ids(session, access.workspace, access.membership)
    if project_id is not None and allowed is not None and project_id not in allowed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")
    query = select(TimeEntry).where(
        TimeEntry.workspace_id == access.workspace.id, TimeEntry.user_id == access.user.id
    )
    if allowed is not None:
        query = query.where(TimeEntry.project_id.in_(allowed))
    if from_date is not None:
        query = query.where(TimeEntry.start_at >= local_day_start(from_date))
    if to_date is not None:
        query = query.where(TimeEntry.start_at < local_day_start(to_date + timedelta(days=1)))
    if project_id is not None:
        query = query.where(TimeEntry.project_id == project_id)
    entries = session.exec(query.order_by(TimeEntry.start_at.desc())).all()
    return [entry_read(entry) for entry in entries]


@router.post("/workspaces/{wid}/entries", status_code=status.HTTP_201_CREATED)
def create_entry(body: TimeEntryCreate, session: SessionDep, access: MemberAccess) -> TimeEntryRead:
    """Registro manual con inicio y fin."""
    ensure_writable(access.workspace)
    validate_catalog(
        session,
        access.workspace.id,
        body.project_id,
        body.category_id,
        body.subcategory_id,
        changed=CATALOG_FIELDS,
        allowed_project_ids=accessible_project_ids(session, access.workspace, access.membership),
    )
    validate_times(body.start_at, body.end_at)
    entry = TimeEntry(
        workspace_id=access.workspace.id,
        user_id=access.user.id,
        project_id=body.project_id,
        category_id=body.category_id,
        subcategory_id=body.subcategory_id,
        title=body.title,
        start_at=body.start_at,
        end_at=body.end_at,
        source="manual",
    )
    save_entry(session, entry)
    return entry_read(entry)


@router.patch("/entries/{entry_id}")
def update_entry(
    entry_id: uuid.UUID, body: TimeEntryUpdate, session: SessionDep, user: CurrentUser
) -> TimeEntryRead:
    """Editar un registro propio. Al cronómetro en marcha no se le pone fin aquí: se para con
    POST /timer/stop."""
    entry, allowed = get_own_entry(session, user, entry_id)
    ensure_writable(session.get_one(Workspace, entry.workspace_id))
    changes = body.model_dump(exclude_unset=True)
    if "end_at" in changes and entry.end_at is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Para parar el cronómetro usa el botón de parar"
        )
    # Solo la sublabel admite null (= quitarla); el resto, si llega, tiene que tener valor.
    for field in ("project_id", "category_id", "title", "start_at", "end_at"):
        if field in changes and changes[field] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{field} no puede ser null")

    for field, value in changes.items():
        setattr(entry, field, value)
    # Si cambia la label y no se dice nada de la sublabel, la anterior ya no vale: se quita.
    if "category_id" in changes and "subcategory_id" not in changes:
        entry.subcategory_id = None

    changed = set(changes) & CATALOG_FIELDS
    if changed:
        validate_catalog(
            session,
            entry.workspace_id,
            entry.project_id,
            entry.category_id,
            entry.subcategory_id,
            changed=changed,
            allowed_project_ids=allowed,
        )
    validate_times(entry.start_at, entry.end_at)
    save_entry(session, entry)
    return entry_read(entry)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> None:
    """Borrar un registro propio (también descarta un cronómetro en marcha).

    Es lo único que se borra de verdad: es un dato tuyo, no algo de lo que dependan otros.
    """
    entry, _ = get_own_entry(session, user, entry_id)
    ensure_writable(session.get_one(Workspace, entry.workspace_id))
    session.delete(entry)
    session.commit()


# --- Cronómetro (uno por persona, en todos sus espacios) ---


@router.post("/workspaces/{wid}/timer/start", status_code=status.HTTP_201_CREATED)
def start_timer(body: TimerStart, session: SessionDep, access: MemberAccess) -> TimeEntryRead:
    """Arranca el cronómetro. Si ya había uno en marcha (en este u otro espacio), lo para
    primero, como hace Clockify."""
    ensure_writable(access.workspace)
    validate_catalog(
        session,
        access.workspace.id,
        body.project_id,
        body.category_id,
        body.subcategory_id,
        changed=CATALOG_FIELDS,
        allowed_project_ids=accessible_project_ids(session, access.workspace, access.membership),
    )
    running = find_running(session, access.user.id)
    if running is not None:
        stop_entry(running)
        session.add(running)
        # Se escribe ya el fin del anterior para que la BD no vea dos cronómetros a la vez.
        session.flush()
    entry = TimeEntry(
        workspace_id=access.workspace.id,
        user_id=access.user.id,
        project_id=body.project_id,
        category_id=body.category_id,
        subcategory_id=body.subcategory_id,
        title=body.title,
        start_at=utc_now(),
        source="timer",
    )
    save_entry(session, entry)
    return entry_read(entry)


@router.post("/timer/stop")
def stop_timer(session: SessionDep, user: CurrentUser) -> TimeEntryRead:
    """Para mi cronómetro, esté en el espacio que esté."""
    running = find_running(session, user.id)
    if running is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay ningún cronómetro en marcha")
    stop_entry(running)
    save_entry(session, running)
    return entry_read(running)


@router.get("/timer/current")
def current_timer(session: SessionDep, user: CurrentUser) -> TimeEntryRead | None:
    """Mi cronómetro en marcha, o null."""
    running = session.exec(
        select(TimeEntry).where(TimeEntry.user_id == user.id, TimeEntry.end_at.is_(None))
    ).first()
    return entry_read(running) if running is not None else None
