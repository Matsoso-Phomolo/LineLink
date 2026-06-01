import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_optional_current_user, require_roles
from app.models import District, DistrictAdminAssignment, User, UserRole
from app.schemas import DistrictResponse, DistrictUpdate

router = APIRouter(prefix="/districts", tags=["districts"])


@router.get("", response_model=list[DistrictResponse])
def list_districts(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> list[District]:
    if current_user and current_user.role == UserRole.district_admin:
        return (
            db.query(District)
            .join(DistrictAdminAssignment, DistrictAdminAssignment.district_id == District.id)
            .filter(
                DistrictAdminAssignment.user_id == current_user.id,
                DistrictAdminAssignment.is_active.is_(True),
            )
            .order_by(District.name.asc())
            .all()
        )

    return db.query(District).order_by(District.name.asc()).all()


@router.get("/active", response_model=list[DistrictResponse])
def list_active_districts(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> list[District]:
    if current_user and current_user.role == UserRole.district_admin:
        return (
            db.query(District)
            .join(DistrictAdminAssignment, DistrictAdminAssignment.district_id == District.id)
            .filter(
                DistrictAdminAssignment.user_id == current_user.id,
                DistrictAdminAssignment.is_active.is_(True),
                District.is_active.is_(True),
            )
            .order_by(District.name.asc())
            .all()
        )

    return (
        db.query(District)
        .filter(District.is_active.is_(True))
        .order_by(District.name.asc())
        .all()
    )


@router.get("/{district_id}", response_model=DistrictResponse)
def get_district(
    district_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> District:
    district = db.query(District).filter(District.id == district_id).first()

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found",
        )

    if current_user and current_user.role == UserRole.district_admin:
        assigned = (
            db.query(DistrictAdminAssignment)
            .filter(
                DistrictAdminAssignment.user_id == current_user.id,
                DistrictAdminAssignment.district_id == district.id,
                DistrictAdminAssignment.is_active.is_(True),
            )
            .first()
        )

        if not assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="District is outside your assigned scope",
            )

    return district


@router.patch("/{district_id}", response_model=DistrictResponse)
def update_district(
    district_id: uuid.UUID,
    payload: DistrictUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
) -> District:
    district = db.query(District).filter(District.id == district_id).first()

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"]:
        district.name = update_data["name"]

    if "description" in update_data:
        district.description = update_data["description"]

    if "is_active" in update_data:
        district.is_active = update_data["is_active"]

        if district.is_active:
            district.rollout_stage = "active"
            district.activated_at = datetime.now(timezone.utc)
        else:
            district.rollout_stage = "locked"
            district.activated_at = None

    db.add(district)
    db.commit()
    db.refresh(district)

    return district
