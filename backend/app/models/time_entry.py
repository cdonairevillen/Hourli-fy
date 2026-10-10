import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Index, column, func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlmodel import Field, SQLModel

from app.models.common import TZDateTime, utc_now


class TimeEntry(SQLModel, table=True):
    """Una tarea registrada: nombre libre + label (+ sublabel) dentro de un proyecto.

    `end_at` null = cronómetro en marcha. La duración no se guarda: es `end_at - start_at`.
    """

    __tablename__ = "time_entries"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_time_entries_end_after_start"),
        CheckConstraint("end_at <= start_at + interval '24 hours'", name="ck_time_entries_max_24h"),
        CheckConstraint("source IN ('manual', 'timer')", name="ck_time_entries_source"),
        # Informes del espacio por fechas y hoja de tiempo de cada persona.
        Index("ix_time_entries_workspace_start", "workspace_id", "start_at"),
        Index("ix_time_entries_user_start", "user_id", "start_at"),
        # Como mucho un cronómetro en marcha por persona (en todos sus espacios).
        Index(
            "uq_time_entries_running",
            "user_id",
            unique=True,
            postgresql_where=text("end_at IS NULL"),
        ),
        # Sin solapes: dos registros de la misma persona no pueden compartir ningún instante.
        # tstzrange(start, NULL) llega hasta el infinito, así que el cronómetro en marcha también
        # cuenta. Necesita la extensión btree_gist (para comparar user_id con = en un índice GiST).
        ExcludeConstraint(
            (column("user_id"), "="),
            (func.tstzrange(column("start_at"), column("end_at")), "&&"),
            name="ex_time_entries_no_overlap",
            using="gist",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    user_id: uuid.UUID = Field(foreign_key="users.id")
    project_id: uuid.UUID = Field(foreign_key="projects.id")
    category_id: uuid.UUID = Field(foreign_key="categories.id")
    subcategory_id: uuid.UUID | None = Field(default=None, foreign_key="subcategories.id")
    title: str
    start_at: datetime = Field(sa_type=TZDateTime)
    end_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    # "manual" (hora de inicio y fin escritas a mano) o "timer" (cronómetro).
    source: str
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
    updated_at: datetime = Field(
        default_factory=utc_now, sa_type=TZDateTime, sa_column_kwargs={"onupdate": func.now()}
    )
