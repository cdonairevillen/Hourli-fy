"""Cuerpos de petición y respuesta de la API (lo que entra y sale en JSON)."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, EmailStr, Field, StringConstraints


class GoogleLogin(BaseModel):
    credential: str


class UserRead(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    avatar_url: str | None
    # False = cuenta solo de Google (puede ponerse una contraseña en Mi cuenta).
    has_password: bool
    # Su email está en ADMIN_EMAILS: puede entrar al panel /admin.
    is_admin: bool


# Mínimo 8 caracteres y sin más reglas (lo que recomienda el NIST). Sin recortar espacios:
# una contraseña puede empezar o acabar en espacio.
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class RegisterBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    email: EmailStr
    password: Password


class LoginBody(BaseModel):
    email: EmailStr
    # Al entrar no se aplica la norma de longitud: solo se compara con la guardada.
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class ForgotPasswordBody(BaseModel):
    email: EmailStr


class ResetPasswordBody(BaseModel):
    token: str
    password: Password


class ChangePasswordBody(BaseModel):
    # Obligatoria si la cuenta ya tiene contraseña; las cuentas de Google la ponen sin ella.
    current_password: str | None = None
    new_password: Password


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class WorkspaceUpdate(BaseModel):
    """Todos los campos son opcionales: solo se cambia lo que llega."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    archived: bool | None = None
    # Transferir la propiedad a otro miembro activo.
    owner_id: uuid.UUID | None = None


class WorkspaceRead(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    archived: bool
    is_owner: bool
    created_at: datetime


class MemberRead(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    avatar_url: str | None
    is_owner: bool
    joined_at: datetime
    # True = ve todos los proyectos del espacio; False = solo los de project_ids.
    all_projects: bool
    project_ids: list[uuid.UUID]
    # Usuario fantasma (horas importadas de alguien sin cuenta): se puede reclamar con un link.
    is_ghost: bool = False


class MemberAccessUpdate(BaseModel):
    """Qué proyectos puede ver un miembro: todos, o solo los de la lista."""

    all_projects: bool
    project_ids: list[uuid.UUID] = []


class InvitationCreate(BaseModel):
    # null = sin límite de usos (solo caduca por fecha).
    max_uses: int | None = Field(default=None, ge=1, le=100)
    # null = invitación al espacio entero; con valor = solo a ese proyecto.
    project_id: uuid.UUID | None = None


InvitationStatus = Literal["active", "expired", "revoked", "exhausted", "archived"]


class InvitationRead(BaseModel):
    id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    max_uses: int | None
    uses: int
    status: InvitationStatus
    # null = invitación al espacio entero.
    project_id: uuid.UUID | None
    project_name: str | None
    # Link para reclamar las horas de un usuario fantasma (null = invitación normal).
    claim_user_name: str | None = None


class InvitationCreated(InvitationRead):
    # El token solo se devuelve al crear: en la BD únicamente queda su hash.
    token: str


class InvitationPreview(BaseModel):
    """Lo que ve quien abre un link, aunque no haya iniciado sesión."""

    workspace_name: str
    owner_name: str
    expires_at: datetime
    status: InvitationStatus
    # Si invita solo a un proyecto (si no, null: al espacio entero).
    project_id: uuid.UUID | None
    project_name: str | None
    # Si es un link para reclamar las horas de un usuario fantasma, su nombre.
    claim_user_name: str | None = None


# --- Catálogo: proyectos, tipologías ("labels") y subtipologías ("sublabels") ---

CatalogName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
# Color en hex: el front ofrece una paleta, pero la API acepta cualquier #RRGGBB.
HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
# Primer color de la paleta del front (frontend/src/components/catalog/ProjectsCard.tsx).
DEFAULT_PROJECT_COLOR = "#2a78d6"


class ProjectCreate(BaseModel):
    name: CatalogName
    color: HexColor = DEFAULT_PROJECT_COLOR


class ProjectUpdate(BaseModel):
    """Solo se cambia lo que llega."""

    name: CatalogName | None = None
    color: HexColor | None = None
    archived: bool | None = None


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    color: str
    archived: bool
    created_at: datetime


class CatalogItemCreate(BaseModel):
    """Crear una tipología o una subtipología: solo lleva nombre."""

    name: CatalogName


class CatalogItemUpdate(BaseModel):
    name: CatalogName | None = None
    archived: bool | None = None


class SubcategoryRead(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    archived: bool


class CategoryRead(BaseModel):
    id: uuid.UUID
    name: str
    archived: bool
    subcategories: list[SubcategoryRead]


# --- Registros de tiempo (tareas) ---

TaskTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
EntrySource = Literal["manual", "timer"]


class TimerStart(BaseModel):
    """Arrancar el cronómetro desde la hoja de un proyecto."""

    project_id: uuid.UUID
    category_id: uuid.UUID
    subcategory_id: uuid.UUID | None = None
    title: TaskTitle


class TimeEntryCreate(TimerStart):
    """Registro manual: como arrancar el cronómetro, pero con inicio y fin escritos.

    Las fechas deben llevar zona horaria (el front manda UTC, p. ej. "2026-10-05T08:00:00Z").
    """

    start_at: AwareDatetime
    end_at: AwareDatetime


class TimeEntryUpdate(BaseModel):
    """Solo se cambia lo que llega. `subcategory_id: null` explícito quita la sublabel."""

    project_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    subcategory_id: uuid.UUID | None = None
    title: TaskTitle | None = None
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None


class TimeEntryRead(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    project_id: uuid.UUID
    category_id: uuid.UUID
    subcategory_id: uuid.UUID | None
    title: str
    start_at: datetime
    # null = cronómetro en marcha.
    end_at: datetime | None
    source: EntrySource
    # null mientras el cronómetro sigue en marcha.
    duration_seconds: int | None


class TaskSuggestion(BaseModel):
    """Una tarea ya hecha, para autocompletar: el título y la label/sublabel de su último uso."""

    title: str
    category_id: uuid.UUID
    subcategory_id: uuid.UUID | None
    last_used_at: datetime


# --- Panel del dueño (informes) ---


class UserTotal(BaseModel):
    user_id: uuid.UUID
    name: str
    total_seconds: int


class ProjectTotal(BaseModel):
    project_id: uuid.UUID
    name: str
    color: str
    total_seconds: int


class CategoryTotal(BaseModel):
    category_id: uuid.UUID
    name: str
    total_seconds: int


class DayTotal(BaseModel):
    # Día en hora de España (AAAA-MM-DD).
    day: date
    total_seconds: int


class ReportSummary(BaseModel):
    """Totales del grupo de registros que cumple los filtros."""

    from_date: date
    to_date: date
    total_seconds: int
    entry_count: int
    by_user: list[UserTotal]
    by_project: list[ProjectTotal]
    by_category: list[CategoryTotal]
    by_day: list[DayTotal]


class ReportEntry(TimeEntryRead):
    """Un registro del panel: como los propios, pero con el nombre de quien lo hizo."""

    user_id: uuid.UUID
    user_name: str


class ReportEntriesPage(BaseModel):
    total: int
    items: list[ReportEntry]


# --- Importar informes de Clockify (PDF "Informe detallado") ---


class ImportPerson(BaseModel):
    """Una persona del PDF, sus horas y a quién se le asignan."""

    # Tal cual sale en el PDF.
    name: str
    entry_count: int
    total_seconds: int
    # Miembro sugerido (mismo nombre, o el email empieza por ese nombre). null = fantasma nuevo.
    user_id: uuid.UUID | None
    user_name: str | None
    is_ghost: bool


class ImportLabel(BaseModel):
    """Una línea "proyecto - tarea" de Clockify y la label/sublabel en la que se guardará."""

    project_line: str
    entry_count: int
    total_seconds: int
    label: str
    sublabel: str | None
    # False = se creará al importar.
    label_exists: bool
    sublabel_exists: bool


class ImportPreview(BaseModel):
    period: str
    # Total de la cabecera del PDF: ya se ha comprobado que cuadra con la suma de las entradas.
    total_seconds: int
    entry_count: int
    first_day: date
    last_day: date
    # Entradas que ya se importaron antes en este espacio (no se volverán a crear).
    duplicate_count: int
    people: list[ImportPerson]
    labels: list[ImportLabel]


class ImportPersonChoice(BaseModel):
    name: str
    # Miembro activo del espacio; null = fantasma (se reutiliza uno con ese nombre si ya existe).
    user_id: uuid.UUID | None = None


class ImportLabelChoice(BaseModel):
    project_line: str
    label: CatalogName
    sublabel: CatalogName | None = None


class ImportOptions(BaseModel):
    """Cómo importar. Lo que no venga se rellena con lo sugerido en la vista previa."""

    # Proyecto destino: uno del espacio, o un nombre (se usa el que se llame así o se crea).
    project_id: uuid.UUID | None = None
    project_name: CatalogName | None = None
    people: list[ImportPersonChoice] = []
    labels: list[ImportLabelChoice] = []


class ImportResult(BaseModel):
    project_id: uuid.UUID
    created_count: int
    # Ya estaban importadas (mismo PDF o informes que se solapan): no se duplican.
    duplicate_count: int
    # Se solapaban con otra de la misma persona: se movieron justo detrás, con la misma duración.
    shifted_count: int
    # Duraban más de 24 h (el máximo de un registro): se partieron en trozos seguidos.
    split_count: int
    # Duraban 0 segundos: no se guardan (no suman nada).
    empty_count: int
    imported_seconds: int
    ghosts_created: list[str]
    labels_created: int
    sublabels_created: int
