"""Eliminar la cuenta (derecho de supresión del RGPD) sin romper los informes de los demás."""

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Membership, ProjectMember, User, Workspace
from app.models.common import utc_now
from app.services.entries import find_running, stop_entry
from app.services.passwords import invalidate_reset_tokens

DELETED_NAME = "Usuario eliminado"


def delete_account(session: Session, user: User) -> None:
    """Anonimiza al usuario en vez de borrar la fila.

    - Antes tiene que transferir o archivar los espacios activos de los que es dueño (409 si no).
    - Se para su cronómetro, sale de todos sus espacios y se borran nombre, email, foto y
      contraseña (y se gastan sus links de recuperación pendientes).
    - Sus horas siguen en los informes, a nombre de "Usuario eliminado".
    - `google_sub` se borra: si vuelve a entrar con Google, es un usuario nuevo.
    """
    owned = session.exec(
        select(Workspace.name).where(Workspace.owner_id == user.id, Workspace.archived.is_(False))
    ).all()
    if owned:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Antes transfiere o archiva tus espacios: " + ", ".join(owned),
        )

    running = find_running(session, user.id)
    if running is not None:
        stop_entry(running)
        session.add(running)

    now = utc_now()
    memberships = session.exec(
        select(Membership).where(Membership.user_id == user.id, Membership.removed_at.is_(None))
    ).all()
    for membership in memberships:
        membership.removed_at = now
        session.add(membership)
    granted = session.exec(
        select(ProjectMember).where(
            ProjectMember.user_id == user.id, ProjectMember.removed_at.is_(None)
        )
    ).all()
    for row in granted:
        row.removed_at = now
        session.add(row)

    # El email es único y obligatorio: se sustituye por uno que no es de nadie (.invalid es un
    # dominio reservado). Sin google_sub, esa cuenta de Google puede volver como usuario nuevo.
    user.name = DELETED_NAME
    user.email = f"eliminado-{user.id}@hourlify.invalid"
    user.google_sub = None
    user.avatar_url = None
    user.password_hash = None
    user.deleted_at = now
    invalidate_reset_tokens(session, user)
    session.add(user)
    session.commit()
