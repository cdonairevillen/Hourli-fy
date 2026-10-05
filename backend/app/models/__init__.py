"""Modelos SQLModel (tablas).

Cada modelo nuevo se importa aquí para que Alembic lo vea al autogenerar migraciones.
"""

from app.models.catalog import Category, Project, Subcategory
from app.models.invitation import Invitation
from app.models.user import User
from app.models.workspace import Membership, Workspace

__all__ = [
    "Category",
    "Invitation",
    "Membership",
    "Project",
    "Subcategory",
    "User",
    "Workspace",
]
