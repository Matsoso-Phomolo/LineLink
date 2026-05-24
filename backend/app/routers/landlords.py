import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.audit import log_action
from app.database import get_db
from app.dependencies import require_roles
from app.identity import next_identifier
from app.models import AuditAction, Landlord, LandlordRequest, LandlordRequestStatus, User, UserRole
from app.schemas import (
    LandlordCreate,
    LandlordManualCreate,
    LandlordOnboardingResult,
    LandlordRead,
    LandlordRequestCreate,
    LandlordRequestDecision,
    LandlordRequestRead,
)

router = APIRouter(prefix="/landlords", tags=["landlords"])


def generate_landlord_number(db: Session) -> str:
    sequence = db.query(Landlord).count() + 1
    while True:
        number = f"LL-LND-{sequence:06d}"
        if not db.query(Landlord).filter(Landlord.system_landlord_number == number).first():
            return number
        sequence += 1


def generated_password() -> str:
    return f"LL-{secrets.token_urlsafe(10)}aA1!"


def ensure_landlord_numbers(db: Session) -> None:
    changed = False
    for landlord in db.query(Landlord).filter(Landlord.system_landlord_number.is_(None)).order_by(Landlord.created_at.asc()).all():
        landlord.system_landlord_number = generate_landlord_number(db)
        changed = True
    if changed:
        db.commit()


def create_landlord_account(
    db: Session,
    *,
    business_name: str,
    full_name: str,
    email: str,
    phone: str | None,
    address: str | None,
    password: str,
) -> Landlord:
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user and existing_user.role != UserRole.landlord:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already belongs to a non-landlord account")
    user = existing_user
    if not user:
        user = User(
            username=next_identifier(db, UserRole.landlord),
            email=email,
            phone=phone,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role=UserRole.landlord,
            is_active=True,
            must_change_password=True,
        )
        db.add(user)
        db.flush()
    user.is_active = True
    user.must_change_password = True
    landlord = db.query(Landlord).filter(Landlord.user_id == user.id).first()
    if landlord:
        landlord.business_name = business_name
        landlord.contact_phone = phone
        landlord.email = email
        landlord.address = address
        landlord.is_active = True
        if not landlord.system_landlord_number:
            landlord.system_landlord_number = generate_landlord_number(db)
        user.username = landlord.system_landlord_number
        return landlord
    landlord = Landlord(
        user_id=user.id,
        business_name=business_name,
        contact_phone=phone,
        email=email,
        address=address,
        system_landlord_number=generate_landlord_number(db),
        is_active=True,
    )
    db.add(landlord)
    db.flush()
    user.username = landlord.system_landlord_number
    return landlord


@router.post("/requests", response_model=LandlordRequestRead)
def create_landlord_request(payload: LandlordRequestCreate, db: Session = Depends(get_db)):
    existing = db.query(LandlordRequest).filter(
        LandlordRequest.email == payload.email,
        LandlordRequest.status == LandlordRequestStatus.pending,
    ).first()
    if existing:
        return existing
    request = LandlordRequest(**payload.model_dump(), status=LandlordRequestStatus.pending)
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.get("/requests", response_model=list[LandlordRequestRead])
def list_landlord_requests(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    return db.query(LandlordRequest).order_by(LandlordRequest.created_at.desc()).all()


@router.post("/requests/{request_id}/approve", response_model=LandlordOnboardingResult)
def approve_landlord_request(
    request_id: uuid.UUID,
    payload: LandlordRequestDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    request = db.get(LandlordRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landlord request not found")
    if request.status == LandlordRequestStatus.rejected:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Rejected landlord request cannot be approved")
    password = payload.password or generated_password()
    landlord = create_landlord_account(
        db,
        business_name=request.business_name,
        full_name=request.full_name,
        email=request.email,
        phone=request.phone,
        address=request.address,
        password=password,
    )
    request.status = LandlordRequestStatus.approved
    request.admin_note = payload.admin_note
    request.landlord_id = landlord.id
    request.approved_by_user_id = admin.id
    request.approved_at = datetime.now(timezone.utc)
    log_action(db, AuditAction.approve_landlord, admin, landlord.id, "LandlordRequest", request.id)
    db.commit()
    db.refresh(request)
    db.refresh(landlord)
    return LandlordOnboardingResult(request=request, landlord=landlord, temporary_password=password if not payload.password else None)


@router.post("/requests/{request_id}/reject", response_model=LandlordRequestRead)
def reject_landlord_request(
    request_id: uuid.UUID,
    payload: LandlordRequestDecision,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    request = db.get(LandlordRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landlord request not found")
    request.status = LandlordRequestStatus.rejected
    request.admin_note = payload.admin_note
    db.commit()
    db.refresh(request)
    return request


@router.post("/manual", response_model=LandlordOnboardingResult)
def manually_create_landlord(payload: LandlordManualCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    landlord = create_landlord_account(
        db,
        business_name=payload.business_name,
        full_name=payload.full_name,
        email=str(payload.email),
        phone=payload.phone,
        address=payload.address,
        password=payload.password,
    )
    db.commit()
    db.refresh(landlord)
    return LandlordOnboardingResult(request=None, landlord=landlord, temporary_password=None)


@router.post("", response_model=LandlordRead)
def create_landlord(payload: LandlordCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    landlord = Landlord(**payload.model_dump(), system_landlord_number=generate_landlord_number(db), is_active=True)
    db.add(landlord)
    db.commit()
    db.refresh(landlord)
    return landlord


@router.get("", response_model=list[LandlordRead])
def list_landlords(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    ensure_landlord_numbers(db)
    return db.query(Landlord).order_by(Landlord.created_at.desc()).all()


@router.post("/{landlord_id}/disable", response_model=LandlordRead)
def disable_landlord(landlord_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    landlord = db.get(Landlord, landlord_id)
    if not landlord:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landlord not found")
    landlord.is_active = False
    landlord.user.is_active = False
    db.commit()
    db.refresh(landlord)
    return landlord


@router.delete("/{landlord_id}", response_model=LandlordRead)
def delete_landlord(landlord_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    landlord = db.get(Landlord, landlord_id)
    if not landlord:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landlord not found")
    landlord.is_active = False
    landlord.user.is_active = False
    db.commit()
    db.refresh(landlord)
    return landlord
