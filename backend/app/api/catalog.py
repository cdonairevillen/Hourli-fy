"""Catálogo de un espacio: proyectos, tipologías ("labels") y subtipologías ("sublabels").

Todos los miembros leen; solo el dueño crea, edita y archiva. Nada se borra.
"""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, delete, select

from app.api.deps import MemberAccess, OwnerAccess, SessionDep, WorkspaceAccess
from app.models import Category, Invitation, Project, ProjectMember, Subcategory, TimeEntry
from app.schemas import (
    CatalogItemCreate,
    CatalogItemUpdate,
    CategoryRead,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    SubcategoryRead,
)
from app.services.access import accessible_project_ids

router = APIRouter(prefix="/workspaces/{wid}", tags=["catalog"])


def ensure_writable(access: WorkspaceAccess) -> None:
    """Un espacio archivado se puede consultar, pero no modificar."""
    if access.workspace.archived:
        raise HTTPException(status.HTTP_409_CONFLICT, "El espacio está archivado")


def save_or_conflict(session: Session, item: SQLModel, duplicate_message: str) -> None:
    """Guarda y convierte un nombre repetido en un 409.

    No se comprueba antes con un SELECT: dos peticiones a la vez pasarían las dos la comprobación.
    La restricción única de la BD es la que decide; aquí solo traducimos su error.
    """
    session.add(item)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, duplicate_message) from error
    session.refresh(item)


def get_project(session: Session, access: WorkspaceAccess, project_id: uuid.UUID) -> Project:
    """El proyecto, si es de este espacio; 404 si no existe o es de otro."""
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != access.workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")
    return project


def get_category(session: Session, access: WorkspaceAccess, category_id: uuid.UUID) -> Category:
    """La tipología, si es de este espacio; 404 si no existe o es de otro."""
    category = session.get(Category, category_id)
    if category is None or category.workspace_id != access.workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Label no encontrada")
    return category


def project_read(project: Project) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        name=project.name,
        color=project.color,
        archived=project.archived,
        created_at=project.created_at,
    )


def subcategory_read(subcategory: Subcategory) -> SubcategoryRead:
    return SubcategoryRead(
        id=subcategory.id,
        category_id=subcategory.category_id,
        name=subcategory.name,
        archived=subcategory.archived,
    )


def category_read(category: Category, subcategories: list[Subcategory]) -> CategoryRead:
    return CategoryRead(
        id=category.id,
        name=category.name,
        archived=category.archived,
        subcategories=[subcategory_read(subcategory) for subcategory in subcategories],
    )


DUPLICATE_PROJECT = "Ya existe un proyecto con ese nombre (si está archivado, desarchívalo)"
DUPLICATE_CATEGORY = "Ya existe una label con ese nombre (si está archivada, desarchívala)"
DUPLICATE_SUBCATEGORY = (
    "Esa label ya tiene una sublabel con ese nombre (si está archivada, desarchívala)"
)


# --- Proyectos ---


@router.get("/projects")
def list_projects(
    session: SessionDep, access: MemberAccess, include_archived: bool = False
) -> list[ProjectRead]:
    """Proyectos del espacio que puedo ver (todos, o solo aquellos a los que me invitaron).

    Por defecto solo los activos (los que salen en la app).
    """
    query = select(Project).where(Project.workspace_id == access.workspace.id)
    allowed = accessible_project_ids(session, access.workspace, access.membership)
    if allowed is not None:
        query = query.where(Project.id.in_(allowed))
    if not include_archived:
        query = query.where(Project.archived.is_(False))
    projects = session.exec(query.order_by(Project.created_at)).all()
    return [project_read(project) for project in projects]


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, session: SessionDep, access: OwnerAccess) -> ProjectRead:
    ensure_writable(access)
    project = Project(workspace_id=access.workspace.id, name=body.name, color=body.color)
    save_or_conflict(session, project, DUPLICATE_PROJECT)
    return project_read(project)


@router.patch("/projects/{project_id}")
def update_project(
    project_id: uuid.UUID, body: ProjectUpdate, session: SessionDep, access: OwnerAccess
) -> ProjectRead:
    """Renombrar, cambiar color o archivar/desarchivar."""
    ensure_writable(access)
    project = get_project(session, access, project_id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    save_or_conflict(session, project, DUPLICATE_PROJECT)
    return project_read(project)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: uuid.UUID, session: SessionDep, access: OwnerAccess) -> None:
    """Borra el proyecto de verdad solo si no tiene ninguna tarea; si tiene, hay que archivarlo."""
    ensure_writable(access)
    project = get_project(session, access, project_id)
    has_entries = session.exec(
        select(TimeEntry.id).where(TimeEntry.project_id == project.id).limit(1)
    ).first()
    if has_entries is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Tiene horas registradas: no se puede borrar, archívalo"
        )
    session.exec(delete(ProjectMember).where(ProjectMember.project_id == project.id))
    session.exec(delete(Invitation).where(Invitation.project_id == project.id))
    session.delete(project)
    session.commit()


# --- Tipologías ("labels") y subtipologías ("sublabels") ---


@router.get("/categories")
def list_categories(
    session: SessionDep, access: MemberAccess, include_archived: bool = False
) -> list[CategoryRead]:
    """Labels del espacio, cada una con sus sublabels. Por defecto solo las activas."""
    category_query = select(Category).where(Category.workspace_id == access.workspace.id)
    subcategory_query = (
        select(Subcategory)
        .join(Category, Category.id == Subcategory.category_id)
        .where(Category.workspace_id == access.workspace.id)
    )
    if not include_archived:
        category_query = category_query.where(Category.archived.is_(False))
        subcategory_query = subcategory_query.where(Subcategory.archived.is_(False))
    categories = session.exec(category_query.order_by(Category.created_at)).all()
    subcategories = session.exec(subcategory_query.order_by(Subcategory.created_at)).all()

    # Dos consultas y se agrupan aquí, en vez de una consulta de sublabels por cada label.
    by_category: dict[uuid.UUID, list[Subcategory]] = {}
    for subcategory in subcategories:
        by_category.setdefault(subcategory.category_id, []).append(subcategory)
    return [category_read(category, by_category.get(category.id, [])) for category in categories]


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(
    body: CatalogItemCreate, session: SessionDep, access: OwnerAccess
) -> CategoryRead:
    ensure_writable(access)
    category = Category(workspace_id=access.workspace.id, name=body.name)
    save_or_conflict(session, category, DUPLICATE_CATEGORY)
    return category_read(category, [])


@router.patch("/categories/{category_id}")
def update_category(
    category_id: uuid.UUID, body: CatalogItemUpdate, session: SessionDep, access: OwnerAccess
) -> CategoryRead:
    """Renombrar o archivar/desarchivar. Archivarla no toca sus sublabels: al no salir la
    label en los desplegables, sus sublabels tampoco."""
    ensure_writable(access)
    category = get_category(session, access, category_id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(category, field, value)
    save_or_conflict(session, category, DUPLICATE_CATEGORY)
    subcategories = session.exec(
        select(Subcategory)
        .where(Subcategory.category_id == category.id)
        .order_by(Subcategory.created_at)
    ).all()
    return category_read(category, list(subcategories))


@router.post("/categories/{category_id}/subcategories", status_code=status.HTTP_201_CREATED)
def create_subcategory(
    category_id: uuid.UUID, body: CatalogItemCreate, session: SessionDep, access: OwnerAccess
) -> SubcategoryRead:
    ensure_writable(access)
    category = get_category(session, access, category_id)
    subcategory = Subcategory(category_id=category.id, name=body.name)
    save_or_conflict(session, subcategory, DUPLICATE_SUBCATEGORY)
    return subcategory_read(subcategory)


@router.patch("/categories/{category_id}/subcategories/{subcategory_id}")
def update_subcategory(
    category_id: uuid.UUID,
    subcategory_id: uuid.UUID,
    body: CatalogItemUpdate,
    session: SessionDep,
    access: OwnerAccess,
) -> SubcategoryRead:
    ensure_writable(access)
    category = get_category(session, access, category_id)
    subcategory = session.get(Subcategory, subcategory_id)
    if subcategory is None or subcategory.category_id != category.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sublabel no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(subcategory, field, value)
    save_or_conflict(session, subcategory, DUPLICATE_SUBCATEGORY)
    return subcategory_read(subcategory)
