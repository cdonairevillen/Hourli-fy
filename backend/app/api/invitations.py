from fastapi import APIRouter, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import CurrentUser, SessionDep
from app.core.security import hash_invitation_token
from app.models import Invitation, Membership, Project, ProjectMember, User, Workspace
from app.models.common import utc_now
from app.schemas import InvitationPreview, WorkspaceRead
from app.services.access import grant_project
from app.services.workspaces import invitation_status, workspace_read

router = APIRouter(prefix="/invitations", tags=["invitations"])


def find_invitation(session: Session, token: str, lock: bool = False) -> Invitation:
    """Busca el link por el hash del token; 404 si no existe."""
    query = select(Invitation).where(Invitation.token_hash == hash_invitation_token(token))
    if lock:
        query = query.with_for_update()
    invitation = session.exec(query).first()
    if invitation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitación no encontrada")
    return invitation


@router.get("/{token}")
def preview_invitation(token: str, session: SessionDep) -> InvitationPreview:
    """A qué espacio (y proyecto) invita el link y si sigue valiendo. Público: se ve antes de
    iniciar sesión."""
    invitation = find_invitation(session, token)
    workspace = session.get_one(Workspace, invitation.workspace_id)
    project = session.get(Project, invitation.project_id) if invitation.project_id else None
    owner = session.get_one(User, workspace.owner_id)
    return InvitationPreview(
        workspace_name=workspace.name,
        owner_name=owner.name,
        expires_at=invitation.expires_at,
        status=invitation_status(invitation, workspace, project),
        project_id=invitation.project_id,
        project_name=project.name if project else None,
    )


@router.post("/{token}/accept")
def accept_invitation(token: str, session: SessionDep, user: CurrentUser) -> WorkspaceRead:
    """Une al usuario al espacio con el alcance del link.

    - Link al espacio: ve todos los proyectos (también si antes solo veía alguno).
    - Link a un proyecto: si no era miembro, entra viendo solo ese proyecto; si ya era miembro
      limitado, se le suma ese proyecto.
    Si el link no le da nada nuevo (ya lo veía), no gasta un uso.
    """
    # FOR UPDATE: dos aceptaciones a la vez no pueden pasarse de max_uses.
    invitation = find_invitation(session, token, lock=True)
    workspace = session.get_one(Workspace, invitation.workspace_id)
    project = session.get(Project, invitation.project_id) if invitation.project_id else None
    if invitation_status(invitation, workspace, project) != "active":
        raise HTTPException(status.HTTP_410_GONE, "La invitación ya no es válida")

    membership = session.get(Membership, (workspace.id, user.id))
    active = membership is not None and membership.removed_at is None
    if active and (membership.all_projects or workspace.owner_id == user.id):
        return workspace_read(workspace, user.id)
    if active and project is not None:
        granted = session.get(ProjectMember, (project.id, user.id))
        if granted is not None and granted.removed_at is None:
            return workspace_read(workspace, user.id)

    if membership is None:
        membership = Membership(workspace_id=workspace.id, user_id=user.id, all_projects=False)
    elif not active:
        # Volver tras salir o ser expulsado: se reactiva la misma fila, sin accesos anteriores.
        membership.removed_at = None
        membership.joined_at = utc_now()
        membership.all_projects = False
    if project is None:
        membership.all_projects = True
    else:
        grant_project(session, project.id, user.id)
    invitation.uses += 1
    session.add(membership)
    session.add(invitation)
    session.commit()
    return workspace_read(workspace, user.id)
