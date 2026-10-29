import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.common import TZDateTime, utc_now


class Project(SQLModel, table=True):
    """Proyecto de un espacio (una producción, un encargo). Cada uno tiene su hoja de tareas."""

    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("workspace_id", "name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Sin index=True: el índice de la restricción única (workspace_id, name) ya sirve para filtrar.
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    name: str
    # Color en hex (#RRGGBB) para distinguir el proyecto en listas y gráficas.
    color: str
    archived: bool = False
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)


class Category(SQLModel, table=True):
    """Tipología ("label" en pantalla): p. ej. "Acto 1", "Gestión". Es del espacio y la usan
    todos sus proyectos."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("workspace_id", "name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Sin index=True: el índice de la restricción única (workspace_id, name) ya sirve para filtrar.
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id")
    name: str
    archived: bool = False
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)


class Subcategory(SQLModel, table=True):
    """Subtipología ("sublabel"): concreta una tipología, p. ej. "Acto 1 › Personajes 3D"."""

    __tablename__ = "subcategories"
    __table_args__ = (UniqueConstraint("category_id", "name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Sin index=True por lo mismo: lo cubre el índice único (category_id, name).
    category_id: uuid.UUID = Field(foreign_key="categories.id")
    name: str
    archived: bool = False
    created_at: datetime = Field(default_factory=utc_now, sa_type=TZDateTime)
