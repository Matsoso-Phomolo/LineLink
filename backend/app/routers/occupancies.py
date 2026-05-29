from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit import log_action
from app.database import get_db
from app.dependencies import require_roles
from app.models import (
    AuditAction,
    ListingStatus,
    Occupancy,
    OnboardingChecklist,
    RoomListing,
    RoomStatus,
    User,
    UserRole,
)
from app.ownership import get_room_in_scope, get_tenant_in_scope, scoped_query
from app.rent_logic import generate_initial_rent_due
from app.schemas import OccupancyCreate, OccupancyRead

router = APIRouter(prefix="/occupancies", tags=["occupancies"])


@router.post("", response_model=OccupancyRead)
def create_occupancy(
    payload: OccupancyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.national_admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    tenant = get_tenant_in_scope(db, user, payload.tenant_id)
    room = get_room_in_scope(db, user, payload.room_id)

    if room.status == RoomStatus.occupied:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room is already occupied",
        )

    occupancy = Occupancy(
        **payload.model_dump(),
        landlord_id=tenant.landlord_id,
    )

    db.add(occupancy)
    db.flush()

    room.status = RoomStatus.occupied

    (
        db.query(RoomListing)
        .filter(
            RoomListing.room_id == room.id,
            RoomListing.status == ListingStatus.published,
        )
        .update(
            {
                "status": ListingStatus.rented,
                "is_public": False,
            }
        )
    )

    checklist = (
        db.query(OnboardingChecklist)
        .filter(OnboardingChecklist.tenant_id == tenant.id)
        .first()
    )

    if checklist:
        checklist.room_assigned = True
        checklist.occupancy_activated = True

    generate_initial_rent_due(db, occupancy)

    log_action(
        db,
        AuditAction.create_occupancy,
        user,
        tenant.landlord_id,
        "Occupancy",
        occupancy.id,
    )

    db.commit()
    db.refresh(occupancy)

    return occupancy


@router.get("", response_model=list[OccupancyRead])
def list_occupancies(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.national_admin,
            UserRole.landlord,
            UserRole.caretaker,
            UserRole.tenant,
        )
    ),
):
    return (
        scoped_query(db, user, Occupancy)
        .order_by(Occupancy.created_at.desc())
        .all()
    )
