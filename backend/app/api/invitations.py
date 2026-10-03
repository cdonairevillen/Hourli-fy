from fastapi import APIRouter, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import CurrentUser, SessionDep
from app.core.security import hash_invitation_token
from app.models import Invitation, Membership, User, Workspace
from app.models.common import utc_now
from app.schemas import InvitationPreview, WorkspaceRead
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
    """A qué espacio invita el link y si sigue valiendo. Público: se ve antes de iniciar sesión."""
    invitation = find_invitation(session, token)
    workspace = session.get_one(Workspace, invitation.workspace_id)
    owner = session.get_one(User, workspace.owner_id)
    return InvitationPreview(
        workspace_name=workspace.name,
        owner_name=owner.name,
        expires_at=invitation.expires_at,
        status=invitation_status(invitation, workspace),
    )


@router.post("/{token}/accept")
def accept_invitation(token: str, session: SessionDep, user: CurrentUser) -> WorkspaceRead:
    """Une al usuario al espacio. Si ya era miembro no gasta un uso del link."""
    # FOR UPDATE: dos aceptaciones a la vez no pueden pasarse de max_uses.
    invitation = find_invitation(session, token, lock=True)
    workspace = session.get_one(Workspace, invitation.workspace_id)
    if invitation_status(invitation, workspace) != "active":
        raise HTTPException(status.HTTP_410_GONE, "La invitación ya no es válida")

    membership = session.get(Membership, (workspace.id, user.id))
    if membership is not None and membership.removed_at is None:
        return workspace_read(workspace, user.id)
    if membership is None:
        membership = Membership(workspace_id=workspace.id, user_id=user.id)
    else:
        # Volver tras salir o ser expulsado: se reactiva la misma fila.
        membership.removed_at = None
        membership.joined_at = utc_now()
    invitation.uses += 1
    session.add(membership)
    session.add(invitation)
    session.commit()
    return workspace_read(workspace, user.id)
