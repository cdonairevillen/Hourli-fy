"""Panel de administración en /admin (SQLAdmin): ver, buscar y editar cualquier tabla.

Solo entran los emails de ADMIN_EMAILS (.env). OJO: edita la base de datos directamente, así
que se salta las reglas de la API (límite de espacios, permisos...). Las restricciones de la
propia BD (sin solapes, máx. 24 h, nombres únicos...) sí se siguen aplicando.
"""

import logging
import uuid

from fastapi import FastAPI, HTTPException
from sqladmin import Admin, ModelView
from sqladmin.audit import LoggingAuditBackend
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session
from starlette.requests import Request

from app.api.deps import is_admin
from app.core.config import settings
from app.core.security import SESSION_COOKIE, read_session_token
from app.db import engine
from app.models import (
    Category,
    Invitation,
    Membership,
    PasswordResetToken,
    Project,
    ProjectMember,
    Subcategory,
    TimeEntry,
    User,
    Workspace,
)
from app.services.passwords import authenticate
from app.services.rate_limit import LOGIN_LIMIT

# Sesiones de BD del panel. Los tests la apuntan a la BD de pruebas con .configure(bind=...).
admin_session_maker = sessionmaker(bind=engine, class_=Session)


def find_admin(user_id: uuid.UUID | None) -> User | None:
    if user_id is None:
        return None
    with admin_session_maker() as session:
        user = session.get(User, user_id)
        return user if user is not None and is_admin(user) else None


class AdminAuth(AuthenticationBackend):
    """Entra quien ya tiene sesión en la app (nuestra cookie) o quien hace login en el formulario
    del panel con email y contraseña. En los dos casos, solo si su email está en ADMIN_EMAILS."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email, password = str(form.get("username", "")), str(form.get("password", ""))
        try:
            client = request.client.host if request.client else "desconocida"
            LOGIN_LIMIT.hit(f"admin|{client}|{email.strip().lower()}")
            with admin_session_maker() as session:
                user = authenticate(session, email, password)
        except HTTPException:
            return False
        if not is_admin(user):
            return False
        request.session["user_id"] = str(user.id)
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return find_admin(self.current_user_id(request)) is not None

    async def get_user_id(self, request: Request) -> str | None:
        """Quién hace cada cambio: lo usa el registro de auditoría."""
        user_id = self.current_user_id(request)
        return str(user_id) if user_id else None

    def current_user_id(self, request: Request) -> uuid.UUID | None:
        from_form = request.session.get("user_id")
        if from_form:
            return uuid.UUID(from_form)
        token = request.cookies.get(SESSION_COOKIE)
        return read_session_token(token) if token else None


# --- Vistas: qué se ve y qué se puede tocar de cada tabla ---
# No se borran usuarios, espacios, proyectos ni labels (de ellos dependen otros datos): se
# archivan editando. Sí se pueden borrar tareas, invitaciones y links de recuperación.


class UserAdmin(ModelView, model=User):
    name_plural = "Usuarios"
    icon = "fa-solid fa-user"
    column_list = ["id", "name", "email", "created_at", "deleted_at"]
    column_searchable_list = ["name", "email"]
    column_sortable_list = ["name", "email", "created_at"]
    # Nunca se muestran ni se editan el hash de la contraseña ni el identificador de Google.
    column_details_exclude_list = ["password_hash", "google_sub"]
    form_excluded_columns = ["password_hash", "google_sub"]
    can_create = False
    can_delete = False


class WorkspaceAdmin(ModelView, model=Workspace):
    name_plural = "Espacios"
    icon = "fa-solid fa-building"
    column_list = ["id", "name", "owner_id", "archived", "created_at"]
    column_searchable_list = ["name"]
    column_sortable_list = ["name", "created_at"]
    can_delete = False


class MembershipAdmin(ModelView, model=Membership):
    name_plural = "Miembros"
    icon = "fa-solid fa-users"
    column_list = ["workspace_id", "user_id", "joined_at", "removed_at"]
    can_delete = False


class ProjectMemberAdmin(ModelView, model=ProjectMember):
    name = "Acceso a proyecto"
    name_plural = "Accesos a proyectos"
    icon = "fa-solid fa-user-lock"
    column_list = ["project_id", "user_id", "added_at", "removed_at"]
    can_delete = False


class InvitationAdmin(ModelView, model=Invitation):
    name_plural = "Invitaciones"
    icon = "fa-solid fa-link"
    column_list = ["id", "workspace_id", "project_id", "expires_at", "max_uses", "uses"]
    column_details_exclude_list = ["token_hash"]
    form_excluded_columns = ["token_hash"]
    # Una invitación creada aquí no tendría link (el token solo existe al crearla en la app).
    can_create = False


class ProjectAdmin(ModelView, model=Project):
    name_plural = "Proyectos"
    icon = "fa-solid fa-folder"
    column_list = ["id", "workspace_id", "name", "color", "archived", "created_at"]
    column_searchable_list = ["name"]
    can_delete = False


class CategoryAdmin(ModelView, model=Category):
    name = "Label"
    name_plural = "Labels"
    icon = "fa-solid fa-tag"
    column_list = ["id", "workspace_id", "name", "archived"]
    column_searchable_list = ["name"]
    can_delete = False


class SubcategoryAdmin(ModelView, model=Subcategory):
    name = "Sublabel"
    name_plural = "Sublabels"
    icon = "fa-solid fa-tags"
    column_list = ["id", "category_id", "name", "archived"]
    column_searchable_list = ["name"]
    can_delete = False


class TimeEntryAdmin(ModelView, model=TimeEntry):
    name = "Tarea"
    name_plural = "Tareas"
    icon = "fa-solid fa-clock"
    column_list = ["id", "user_id", "workspace_id", "title", "start_at", "end_at", "source"]
    column_searchable_list = ["title"]
    column_sortable_list = ["start_at", "end_at"]
    column_default_sort = ("start_at", True)


class PasswordResetTokenAdmin(ModelView, model=PasswordResetToken):
    name = "Link de recuperación"
    name_plural = "Links de recuperación"
    icon = "fa-solid fa-key"
    column_list = ["id", "user_id", "expires_at", "used_at", "created_at"]
    column_details_exclude_list = ["token_hash"]
    form_excluded_columns = ["token_hash"]
    can_create = False
    can_edit = False


ADMIN_VIEWS = [
    UserAdmin,
    WorkspaceAdmin,
    MembershipAdmin,
    ProjectMemberAdmin,
    InvitationAdmin,
    ProjectAdmin,
    CategoryAdmin,
    SubcategoryAdmin,
    TimeEntryAdmin,
    PasswordResetTokenAdmin,
]


def setup_admin(app: FastAPI) -> Admin:
    """Monta el panel en /admin."""
    admin = Admin(
        app,
        session_maker=admin_session_maker,
        base_url="/admin",
        title="Hourli-fy · Admin",
        authentication_backend=AdminAuth(
            secret_key=settings.secret_key,
            # Otro nombre: "session" es ya la cookie de la app y la pisaría.
            session_cookie="admin_session",
            https_only=settings.cookie_secure,
        ),
        # Cada alta, cambio o borrado queda en el log con quién lo hizo. Nivel WARNING para que
        # se vea aunque no haya configuración de logging.
        audit_backend=LoggingAuditBackend(level=logging.WARNING),
    )
    for view in ADMIN_VIEWS:
        admin.add_view(view)
    return admin
