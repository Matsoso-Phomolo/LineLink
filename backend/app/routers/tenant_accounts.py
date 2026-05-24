from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.database import get_db
from app.dependencies import get_actor_landlord_id, require_roles
from app.identity import next_identifier
from app.models import Tenant, TenantInvitation, User, UserRole, InvitationStatus
from app.schemas import TenantInvitationAccept, TenantInvitationCreate, TenantInvitationRead

router = APIRouter(prefix="/tenant-invitations", tags=["tenant invitations"])


@router.post("", response_model=TenantInvitationRead)
def create_invitation(payload: TenantInvitationCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    import uuid

    invitation = TenantInvitation(
        landlord_id=get_actor_landlord_id(db, user),
        tenant_application_id=payload.tenant_application_id,
        tenant_id=payload.tenant_id,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        token=str(uuid.uuid4()),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.post("/accept")
def accept_invitation(payload: TenantInvitationAccept, db: Session = Depends(get_db)):
    invitation = db.query(TenantInvitation).filter(TenantInvitation.token == payload.token, TenantInvitation.status == InvitationStatus.pending).first()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    user = User(username=next_identifier(db, UserRole.tenant), email=str(payload.email), phone=payload.phone, full_name=payload.full_name, role=UserRole.tenant, hashed_password=get_password_hash(payload.password))
    db.add(user)
    db.flush()
    if invitation.tenant_id:
        tenant = db.get(Tenant, invitation.tenant_id)
        tenant.user_id = user.id
    invitation.status = InvitationStatus.accepted
    db.commit()
    return {"user_id": user.id, "tenant_id": invitation.tenant_id}
