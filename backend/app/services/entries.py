"""Reglas de los registros de tiempo que usan las rutas de registros y del cronómetro."""

import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import Category, Project, Subcategory, TimeEntry
from app.models.common import utc_now
from app.schemas import TimeEntryRead

MAX_DURATION = timedelta(hours=24)
# Las fechas se guardan en UTC, pero los días (filtros, quincenas) son los de España.
LOCAL_TZ = ZoneInfo("Europe/Madrid")

# Errores de la BD (por nombre de restricción) → respuesta clara para el usuario.
CONSTRAINT_ERRORS = {
    "ex_time_entries_no_overlap": (
        status.HTTP_409_CONFLICT,
        "Se solapa con otro registro tuyo (o con el cronómetro en marcha)",
    ),
    "uq_time_entries_running": (status.HTTP_409_CONFLICT, "Ya tienes un cronómetro en marcha"),
    "ck_time_entries_end_after_start": (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "El fin debe ser posterior al inicio",
    ),
    "ck_time_entries_max_24h": (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Un registro no puede durar más de 24 horas",
    ),
}


def local_day_start(day: date) -> datetime:
    """Las 00:00 de ese día en España, como instante (lo que se compara con start_at)."""
    return datetime.combine(day, time.min, tzinfo=LOCAL_TZ)


def entry_read(entry: TimeEntry) -> TimeEntryRead:
    duration = None
    if entry.end_at is not None:
        duration = int((entry.end_at - entry.start_at).total_seconds())
    return TimeEntryRead(
        id=entry.id,
        workspace_id=entry.workspace_id,
        project_id=entry.project_id,
        category_id=entry.category_id,
        subcategory_id=entry.subcategory_id,
        title=entry.title,
        start_at=entry.start_at,
        end_at=entry.end_at,
        source=entry.source,
        duration_seconds=duration,
    )


def invalid(message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, message)


def validate_catalog(
    session: Session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    category_id: uuid.UUID,
    subcategory_id: uuid.UUID | None,
    changed: set[str],
    allowed_project_ids: set | None = None,
) -> None:
    """Proyecto, label y sublabel deben existir en este espacio y la sublabel ser de la label.

    "No archivado" solo se exige a lo que se está eligiendo ahora (`changed`): así se pueden
    corregir las horas de un registro antiguo cuya label se archivó después.
    """
    project = session.get(Project, project_id)
    # allowed_project_ids: los proyectos que ve un miembro limitado (None = todos). Uno al que no
    # tiene acceso se trata igual que uno que no existe.
    not_allowed = allowed_project_ids is not None and project_id not in allowed_project_ids
    if project is None or project.workspace_id != workspace_id or not_allowed:
        raise invalid("El proyecto no existe en este espacio")
    if "project_id" in changed and project.archived:
        raise invalid("El proyecto está archivado")

    category = session.get(Category, category_id)
    if category is None or category.workspace_id != workspace_id:
        raise invalid("La label no existe en este espacio")
    if "category_id" in changed and category.archived:
        raise invalid("La label está archivada")

    if subcategory_id is None:
        return
    subcategory = session.get(Subcategory, subcategory_id)
    if subcategory is None or subcategory.category_id != category.id:
        raise invalid("La sublabel no pertenece a esa label")
    if "subcategory_id" in changed and subcategory.archived:
        raise invalid("La sublabel está archivada")


def validate_times(start_at: datetime, end_at: datetime | None) -> None:
    """Las mismas reglas que las restricciones de la BD, pero con un mensaje claro."""
    if end_at is None:
        return
    if end_at <= start_at:
        raise invalid("El fin debe ser posterior al inicio")
    if end_at - start_at > MAX_DURATION:
        raise invalid("Un registro no puede durar más de 24 horas")


def save_entry(session: Session, entry: TimeEntry) -> None:
    """Guarda y traduce las restricciones de la BD (solapes, un cronómetro...) a 409/422.

    Los solapes no se comprueban antes con un SELECT: con dos peticiones a la vez las dos lo
    pasarían. La restricción de exclusión de Postgres es la que no se puede saltar.
    """
    session.add(entry)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        code, message = CONSTRAINT_ERRORS.get(
            constraint, (status.HTTP_409_CONFLICT, "No se pudo guardar el registro")
        )
        raise HTTPException(code, message) from error
    session.refresh(entry)


def find_running(session: Session, user_id: uuid.UUID) -> TimeEntry | None:
    """Cronómetro en marcha del usuario (en cualquier espacio), bloqueado hasta el commit."""
    return session.exec(
        select(TimeEntry)
        .where(TimeEntry.user_id == user_id, TimeEntry.end_at.is_(None))
        .with_for_update()
    ).first()


def stop_entry(entry: TimeEntry) -> None:
    """Para el cronómetro ahora. Si se quedó encendido más de 24 h, se corta en 24 h
    (un registro no puede durar más) y la persona lo corrige a mano si hace falta."""
    entry.end_at = min(utc_now(), entry.start_at + MAX_DURATION)
