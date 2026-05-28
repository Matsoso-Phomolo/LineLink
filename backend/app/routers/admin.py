import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.admin_ai_risk import build_ai_risk_center
from app.auth import get_password_hash
from app.database import get_db
from app.dependencies import require_roles
from app.identity import next_identifier
from app.models import District, DistrictAdminAssignment, User, UserRole
from app.reminders import run_reminders

router = APIRouter(prefix="/admin", tags=["admin"])


class DistrictAdminCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8)
    district_id: uuid.UUID


class DistrictAdminRead(BaseModel):
    id: uuid.UUID
    username: str | None = None
    full_name: str
    email: str
    phone: str | None = None
    role: UserRole
    is_active: bool
    district_id: uuid.UUID
    district_name: str

    class Config:
        from_attributes = True


@router.post("/run-reminders")
def run_platform_reminders(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    return run_reminders(db)


@router.get("/ai-risk-center")
def ai_risk_center(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    return build_ai_risk_center(db)


@router.post("/district-admins", response_model=DistrictAdminRead)
def create_district_admin(
    payload: DistrictAdminCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    district = db.get(District, payload.district_id)

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found",
        )

    existing_user = db.query(User).filter(User.email == payload.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    if payload.phone:
        existing_phone = db.query(User).filter(User.phone == payload.phone).first()

        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this phone number already exists",
            )

    district_admin = User(
        username=next_identifier(db, UserRole.district_admin),
        email=payload.email,
        phone=payload.phone,
        full_name=payload.full_name,
        role=UserRole.district_admin,
        hashed_password=get_password_hash(payload.password),
        is_active=True,
        must_change_password=True,
    )

    db.add(district_admin)
    db.flush()

    assignment = DistrictAdminAssignment(
        user_id=district_admin.id,
        district_id=district.id,
        is_active=True,
    )

    db.add(assignment)
    db.commit()
    db.refresh(district_admin)
    db.refresh(assignment)

    return DistrictAdminRead(
        id=district_admin.id,
        username=district_admin.username,
        full_name=district_admin.full_name,
        email=district_admin.email,
        phone=district_admin.phone,
        role=district_admin.role,
        is_active=district_admin.is_active,
        district_id=district.id,
        district_name=district.name,
    )


@router.get("/district-admins", response_model=list[DistrictAdminRead])
def list_district_admins(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    rows = (
        db.query(User, DistrictAdminAssignment, District)
        .join(DistrictAdminAssignment, DistrictAdminAssignment.user_id == User.id)
        .join(District, District.id == DistrictAdminAssignment.district_id)
        .filter(User.role == UserRole.district_admin)
        .order_by(District.name.asc(), User.full_name.asc())
        .all()
    )

    return [
        DistrictAdminRead(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            is_active=user.is_active and assignment.is_active,
            district_id=district.id,
            district_name=district.name,
        )
        for user, assignment, district in rows
    ]


@router.post("/district-admins/{user_id}/disable")
def disable_district_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    user = db.get(User, user_id)

    if not user or user.role != UserRole.district_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District admin not found",
        )

    user.is_active = False

    db.query(DistrictAdminAssignment).filter(
        DistrictAdminAssignment.user_id == user.id
    ).update({"is_active": False})

    db.commit()

    return {"detail": "District admin disabled"}


@router.post("/district-admins/{user_id}/enable")
def enable_district_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    user = db.get(User, user_id)

    if not user or user.role != UserRole.district_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District admin not found",
        )

    user.is_active = True

    db.query(DistrictAdminAssignment).filter(
        DistrictAdminAssignment.user_id == user.id
    ).update({"is_active": True})

    db.commit()

    return {"detail": "District admin enabled"}
