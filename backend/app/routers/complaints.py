import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Complaint, Tenant, User, UserRole
from app.ownership import assert_landlord_access, landlord_scope_filter
from app.schemas import ComplaintCreate, ComplaintRead, ComplaintUpdate

router = APIRouter(prefix="/complaints", tags=["complaints"])


def infer_landlord_id(db: Session, user: User, payload: ComplaintCreate) -> uuid.UUID | None:
    if user.role == UserRole.landlord and user.landlord_profile:
        return user.landlord_profile.id
    if user.role == UserRole.caretaker and user.caretaker_profile:
        return user.caretaker_profile.landlord_id
    if user.role == UserRole.tenant:
        tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()
        return tenant.landlord_id if tenant else None
    return None


@router.post("", response_model=ComplaintRead)
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    landlord_id = infer_landlord_id(db, user, payload)
    if payload.property_id and landlord_id:
        # Keeps reports inside the sender's landlord scope when a property is supplied.
        assert_landlord_access(db, user, landlord_id)
    complaint = Complaint(sender_user_id=user.id, landlord_id=landlord_id, **payload.model_dump())
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("", response_model=list[ComplaintRead])
def list_complaints(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == UserRole.tenant:
        return db.query(Complaint).filter((Complaint.sender_user_id == user.id) | (Complaint.receiver_user_id == user.id)).order_by(Complaint.created_at.desc()).all()
    if user.role == UserRole.admin:
        return db.query(Complaint).order_by(Complaint.created_at.desc()).all()
    return landlord_scope_filter(db, user, Complaint).order_by(Complaint.created_at.desc()).all()


@router.put("/{complaint_id}", response_model=ComplaintRead)
def update_complaint(complaint_id: uuid.UUID, payload: ComplaintUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    if user.role == UserRole.tenant and complaint.sender_user_id != user.id and complaint.receiver_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Complaint is outside your scope")
    if user.role in {UserRole.landlord, UserRole.caretaker} and complaint.landlord_id:
        assert_landlord_access(db, user, complaint.landlord_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(complaint, key, value)
    db.commit()
    db.refresh(complaint)
    return complaint
