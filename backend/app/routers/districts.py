import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models import District, User
from app.schemas import DistrictResponse, DistrictUpdate

router = APIRouter(prefix="/districts", tags=["districts"])


def require_admin_user(current_user: User) -> None:
    if str(current_user.role).lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.get("", response_model=list[DistrictResponse])
def list_districts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[District]:
    require_admin_user(current_user)

    return (
        db.query(District)
        .order_by(District.name.asc())
        .all()
    )


@router.get("/active", response_model=list[DistrictResponse])
def list_active_districts(
    db: Session = Depends(get_db),
) -> list[District]:
    return (
        db.query(District)
        .filter(District.is_active.is_(True))
        .order_by(District.name.asc())
        .all()
    )


@router.patch("/{district_id}", response_model=DistrictResponse)
def update_district(
    district_id: uuid.UUID,
    payload: DistrictUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> District:
    require_admin_user(current_user)

    district = (
        db.query(District)
        .filter(District.id == district_id)
        .first()
    )

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data:
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
