"""Importar a un espacio las horas de un PDF "Informe detallado" de Clockify.

Lo usan la ruta del dueño (`api/imports.py`) y el panel de admin (`admin.py`). Va en dos pasos
y sin guardar nada entre ellos: el PDF se vuelve a mandar al confirmar.

1. `build_preview`: lee el PDF, comprueba que cuadra con su total y sugiere a quién asignar cada
   persona y en qué label/sublabel va cada "proyecto - tarea" de Clockify.
2. `run_import`: con lo elegido (o lo sugerido), crea fantasmas, labels y registros.

Cómo se traduce Clockify a este modelo:
- Todo va a UN proyecto de la app (el que se elija): en Clockify los "proyectos" eran partes del
  juego ("Walking sim", "Reuniones"...), que aquí son labels.
- "Scripts & scores - Banda sonora - Jaleo" → label "Scripts & scores", sublabel
  "Banda sonora - Jaleo" (primer trozo = label; el resto = sublabel).
- Las horas del PDF son de España: se pasan a UTC. El fin se calcula como inicio + duración (la
  duración es lo que suma el total; así también sale bien el día del cambio de hora).
"""

import bisect
import hashlib
import unicodedata
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import Category, Membership, Project, Subcategory, TimeEntry, User, Workspace
from app.schemas import (
    DEFAULT_PROJECT_COLOR,
    ImportLabel,
    ImportOptions,
    ImportPerson,
    ImportPreview,
    ImportResult,
)
from app.services.access import grant_project, has_all_projects
from app.services.clockify_pdf import (
    ClockifyPdfError,
    ParsedEntry,
    ParsedReport,
    parse_clockify_pdf,
    split_project_line,
)
from app.services.entries import LOCAL_TZ, MAX_DURATION
from app.services.ghosts import create_ghost

MAX_PDF_BYTES = 20 * 1024 * 1024
# Los nombres del catálogo admiten 80 caracteres y los títulos de tarea 200.
MAX_NAME = 80
MAX_TITLE = 200
NO_LABEL = "Sin label"
NO_TITLE = "(Sin descripción)"


def read_report(data: bytes) -> ParsedReport:
    """Lee el PDF y exige que la suma de sus entradas cuadre al segundo con el total.

    Si no cuadra, algo no se ha leído bien: mejor no importar nada que importar a medias.
    """
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "El PDF pasa de 20 MB")
    try:
        report = parse_clockify_pdf(data)
    except ClockifyPdfError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    if not report.entries:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El PDF no tiene entradas")
    if report.entries_seconds != report.total_seconds:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Las entradas suman {format_seconds(report.entries_seconds)} pero el PDF dice "
            f"{format_seconds(report.total_seconds)}: no se ha leído bien, no se importa nada",
        )
    return report


def format_seconds(seconds: int) -> str:
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def normalize_name(name: str) -> str:
    """Para comparar nombres: sin tildes, sin mayúsculas y sin espacios de más."""
    decomposed = unicodedata.normalize("NFKD", name)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(plain.casefold().split())


def default_label(project_line: str) -> tuple[str, str | None]:
    """ "Scripts & scores - Banda sonora - Jaleo" → ("Scripts & scores", "Banda sonora - Jaleo")."""
    parts = split_project_line(project_line)
    if not parts:
        return NO_LABEL, None
    sublabel = " - ".join(parts[1:])[:MAX_NAME].strip()
    return parts[0][:MAX_NAME].strip(), sublabel or None


def import_key(entry: ParsedEntry) -> str:
    """Huella de la entrada tal cual está en Clockify (persona, horas, texto).

    No depende de a quién se asigne ni de si luego se mueve por un solape: reimportar el mismo PDF
    (o uno que se solape en fechas) da las mismas huellas y esas entradas se saltan.
    """
    raw = "|".join(
        [
            normalize_name(entry.user_name),
            entry.start.isoformat(),
            entry.end.isoformat(),
            str(entry.duration_seconds),
            entry.description,
            entry.project_line,
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def to_utc(local: datetime) -> datetime:
    """Hora de España sin zona → instante en UTC. En la hora repetida del cambio de octubre
    se toma la primera (fold=0), que es lo que hace también Python por defecto."""
    return local.replace(tzinfo=LOCAL_TZ).astimezone(UTC)


def active_members(session: Session, workspace_id: uuid.UUID) -> list[tuple[Membership, User]]:
    return list(
        session.exec(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.workspace_id == workspace_id, Membership.removed_at.is_(None))
        ).all()
    )


def suggest_member(name: str, members: list[User]) -> User | None:
    """Miembro con el mismo nombre (sin tildes ni mayúsculas) o cuyo email empieza por ese
    nombre (Clockify enseña "cdonaire96" a quien no puso nombre). Si hay dudas, ninguno."""
    wanted = normalize_name(name)
    same_name = [user for user in members if normalize_name(user.name) == wanted]
    if len(same_name) == 1:
        return same_name[0]
    same_email = [
        user
        for user in members
        if not user.is_ghost and normalize_name(user.email.split("@")[0]) == wanted
    ]
    return same_email[0] if len(same_email) == 1 else None


def existing_keys(session: Session, workspace_id: uuid.UUID, keys: set[str]) -> set[str]:
    if not keys:
        return set()
    return set(
        session.exec(
            select(TimeEntry.import_key).where(
                TimeEntry.workspace_id == workspace_id, TimeEntry.import_key.in_(keys)
            )
        ).all()
    )


def find_category(session: Session, workspace_id: uuid.UUID, name: str) -> Category | None:
    return session.exec(
        select(Category).where(
            Category.workspace_id == workspace_id, func.lower(Category.name) == name.lower()
        )
    ).first()


def find_subcategory(session: Session, category_id: uuid.UUID, name: str) -> Subcategory | None:
    return session.exec(
        select(Subcategory).where(
            Subcategory.category_id == category_id, func.lower(Subcategory.name) == name.lower()
        )
    ).first()


def build_preview(session: Session, workspace: Workspace, report: ParsedReport) -> ImportPreview:
    """Qué pasaría al importar con lo sugerido. No cambia nada."""
    members = [user for _, user in active_members(session, workspace.id)]
    by_person: dict[str, list[ParsedEntry]] = defaultdict(list)
    by_line: dict[str, list[ParsedEntry]] = defaultdict(list)
    for entry in report.entries:
        by_person[entry.user_name].append(entry)
        by_line[entry.project_line].append(entry)

    people = []
    for name, entries in sorted(by_person.items(), key=lambda item: -len(item[1])):
        user = suggest_member(name, members)
        people.append(
            ImportPerson(
                name=name,
                entry_count=len(entries),
                total_seconds=sum(entry.duration_seconds for entry in entries),
                user_id=user.id if user else None,
                user_name=user.name if user else None,
                is_ghost=user.is_ghost if user else True,
            )
        )

    labels = []
    for line, entries in sorted(by_line.items()):
        label, sublabel = default_label(line)
        category = find_category(session, workspace.id, label)
        subcategory = (
            find_subcategory(session, category.id, sublabel) if category and sublabel else None
        )
        labels.append(
            ImportLabel(
                project_line=line,
                entry_count=len(entries),
                total_seconds=sum(entry.duration_seconds for entry in entries),
                label=label,
                sublabel=sublabel,
                label_exists=category is not None,
                sublabel_exists=sublabel is None or subcategory is not None,
            )
        )

    keys = {import_key(entry) for entry in report.entries}
    days = [entry.start.date() for entry in report.entries]
    return ImportPreview(
        period=report.period,
        total_seconds=report.total_seconds,
        entry_count=len(report.entries),
        first_day=min(days),
        last_day=max(days),
        duplicate_count=len(existing_keys(session, workspace.id, keys)),
        people=people,
        labels=labels,
    )


@dataclass
class ImportCounters:
    created: int = 0
    duplicates: int = 0
    shifted: int = 0
    split: int = 0
    empty: int = 0
    seconds: int = 0
    labels: int = 0
    sublabels: int = 0


def resolve_project(session: Session, workspace: Workspace, options: ImportOptions) -> Project:
    if options.project_id is not None:
        project = session.get(Project, options.project_id)
        if project is None or project.workspace_id != workspace.id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "El proyecto no es de este espacio"
            )
        return project
    if not options.project_name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Elige el proyecto de destino")
    project = session.exec(
        select(Project).where(
            Project.workspace_id == workspace.id,
            func.lower(Project.name) == options.project_name.lower(),
        )
    ).first()
    if project is None:
        project = Project(
            workspace_id=workspace.id, name=options.project_name, color=DEFAULT_PROJECT_COLOR
        )
        session.add(project)
        session.flush()
    return project


def resolve_people(
    session: Session,
    workspace: Workspace,
    names: list[str],
    options: ImportOptions,
    project: Project,
) -> tuple[dict[str, User], list[str]]:
    """Persona del PDF → usuario. Crea los fantasmas que falten y da acceso al proyecto."""
    rows = active_members(session, workspace.id)
    members = {user.id: (membership, user) for membership, user in rows}
    chosen = {choice.name: choice.user_id for choice in options.people}
    people: dict[str, User] = {}
    ghosts_created: list[str] = []
    for name in names:
        if name in chosen:
            user_id = chosen[name]
        else:
            suggested = suggest_member(name, [user for _, user in rows])
            user_id = suggested.id if suggested else None
        if user_id is not None and user_id not in members:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"{name}: no es miembro de este espacio"
            )
        if user_id is None:
            # Fantasma: se reutiliza el de ese nombre si una importación anterior ya lo creó.
            same = [
                user
                for _, user in rows
                if user.is_ghost and normalize_name(user.name) == normalize_name(name)
            ]
            if same:
                user_id = same[0].id
            else:
                ghost = create_ghost(session, workspace.id, name[:MAX_NAME])
                membership = session.get_one(Membership, (workspace.id, ghost.id))
                members[ghost.id] = (membership, ghost)
                rows.append((membership, ghost))
                ghosts_created.append(name)
                user_id = ghost.id
        membership, user = members[user_id]
        # Que vea en su hoja el proyecto donde se le ponen las horas.
        if not has_all_projects(workspace, membership):
            grant_project(session, project.id, user.id)
        people[name] = user
    return people, ghosts_created


def resolve_labels(
    session: Session,
    workspace: Workspace,
    lines: list[str],
    options: ImportOptions,
    counters: ImportCounters,
) -> dict[str, tuple[uuid.UUID, uuid.UUID | None]]:
    """Línea de Clockify → (label, sublabel). Usa las que ya existan (por nombre) o las crea."""
    chosen = {choice.project_line: (choice.label, choice.sublabel) for choice in options.labels}
    result: dict[str, tuple[uuid.UUID, uuid.UUID | None]] = {}
    for line in lines:
        label, sublabel = chosen.get(line) or default_label(line)
        category = find_category(session, workspace.id, label)
        if category is None:
            category = Category(workspace_id=workspace.id, name=label)
            session.add(category)
            session.flush()
            counters.labels += 1
        subcategory = None
        if sublabel:
            subcategory = find_subcategory(session, category.id, sublabel)
            if subcategory is None:
                subcategory = Subcategory(category_id=category.id, name=sublabel)
                session.add(subcategory)
                session.flush()
                counters.sublabels += 1
        result[line] = (category.id, subcategory.id if subcategory else None)
    return result


def busy_intervals(session: Session, user_id: uuid.UUID, since: datetime) -> list:
    """Huecos ya ocupados por la persona (en cualquier espacio), ordenados.

    Un cronómetro en marcha ocupa hasta ahora mismo.
    """
    rows = session.exec(
        select(TimeEntry.start_at, TimeEntry.end_at).where(
            TimeEntry.user_id == user_id,
            (TimeEntry.end_at > since) | TimeEntry.end_at.is_(None),
        )
    ).all()
    now = datetime.now(tz=LOCAL_TZ)
    return sorted((start, end or max(now, start)) for start, end in rows)


def place(intervals: list, start: datetime, duration: timedelta) -> datetime:
    """Primer inicio >= `start` donde cabe `duration` sin solaparse con `intervals` (ordenados y
    sin solapes entre sí). Mete el hueco elegido en `intervals`."""
    index = bisect.bisect_right(intervals, (start, start))
    if index > 0 and intervals[index - 1][1] > start:
        start = intervals[index - 1][1]
    while index < len(intervals) and intervals[index][0] < start + duration:
        start = max(start, intervals[index][1])
        index += 1
    bisect.insort(intervals, (start, start + duration))
    return start


def run_import(
    session: Session, workspace: Workspace, report: ParsedReport, options: ImportOptions
) -> ImportResult:
    """Importa todo en una sola transacción: o entra el PDF entero o nada.

    - Se saltan las entradas ya importadas en este espacio (misma huella).
    - La BD no deja que una persona tenga dos registros a la vez, pero Clockify sí: si una
      entrada se solapa con otra de esa persona, se mueve justo detrás conservando su duración
      (así los totales siguen cuadrando).
    - Un registro dura como mucho 24 h: las entradas más largas se parten en trozos seguidos.
    - Las entradas de 0 segundos no se guardan (no suman nada).
    """
    if workspace.archived:
        raise HTTPException(status.HTTP_409_CONFLICT, "El espacio está archivado")
    counters = ImportCounters()
    project = resolve_project(session, workspace, options)

    # Primero se descartan las ya importadas: así no se crean fantasmas ni labels de más.
    keyed = [(import_key(entry), entry) for entry in report.entries]
    already = existing_keys(session, workspace.id, {key for key, _ in keyed})
    fresh: list[tuple[str, ParsedEntry]] = []
    for key, entry in keyed:
        if key in already:
            counters.duplicates += 1
        elif entry.duration_seconds == 0:
            # Clockify guarda entradas de 0 s; aquí un registro tiene que durar algo.
            counters.empty += 1
        else:
            already.add(key)
            fresh.append((key, entry))

    names = list(dict.fromkeys(entry.user_name for _, entry in fresh))
    lines = list(dict.fromkeys(entry.project_line for _, entry in fresh))
    people, ghosts_created = resolve_people(session, workspace, names, options, project)
    labels = resolve_labels(session, workspace, lines, options, counters)
    pending: dict[uuid.UUID, list[tuple[str, ParsedEntry]]] = defaultdict(list)
    for key, entry in fresh:
        pending[people[entry.user_name].id].append((key, entry))

    for user_id, entries in pending.items():
        entries.sort(key=lambda item: (item[1].start, item[0]))
        first_start = to_utc(entries[0][1].start)
        intervals = busy_intervals(session, user_id, first_start)
        for key, entry in entries:
            original_start = to_utc(entry.start)
            remaining = timedelta(seconds=entry.duration_seconds)
            start = original_start
            chunks = 0
            while remaining > timedelta(0):
                piece = min(remaining, MAX_DURATION)
                start = place(intervals, start, piece)
                if chunks == 0 and start != original_start:
                    counters.shifted += 1
                category_id, subcategory_id = labels[entry.project_line]
                session.add(
                    TimeEntry(
                        workspace_id=workspace.id,
                        user_id=user_id,
                        project_id=project.id,
                        category_id=category_id,
                        subcategory_id=subcategory_id,
                        title=(entry.description or NO_TITLE)[:MAX_TITLE],
                        start_at=start,
                        end_at=start + piece,
                        source="manual",
                        # Los trozos de una entrada partida llevan su número detrás.
                        import_key=key if chunks == 0 else f"{key}#{chunks}",
                    )
                )
                start += piece
                remaining -= piece
                chunks += 1
            counters.created += 1
            if chunks > 1:
                counters.split += 1
            counters.seconds += entry.duration_seconds

    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se pudo importar (¿otra importación a la vez?). No se ha guardado nada",
        ) from error
    return ImportResult(
        project_id=project.id,
        created_count=counters.created,
        duplicate_count=counters.duplicates,
        shifted_count=counters.shifted,
        split_count=counters.split,
        empty_count=counters.empty,
        imported_seconds=counters.seconds,
        ghosts_created=ghosts_created,
        labels_created=counters.labels,
        sublabels_created=counters.sublabels,
    )
