import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import (
    ListingStatus,
    Occupancy,
    OccupancyStatus,
    Room,
    RoomListing,
    RoomStatus,
    User,
    UserRole,
)
from app.ownership import get_property_in_scope, get_room_in_scope, scoped_query
from app.schemas import RoomCreate, RoomRead, RoomUpdate

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=RoomRead)
def create_room(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin, UserRole.district_admin)),
):
    prop = get_property_in_scope(db, user, payload.property_id)

    room = Room(
        **payload.model_dump(),
        landlord_id=prop.landlord_id,
    )

    db.add(room)
    db.commit()
    db.refresh(room)

    return room


@router.get("", response_model=list[RoomRead])
def list_rooms(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        scoped_query(db, user, Room)
        .order_by(Room.created_at.desc())
        .all()
    )


@router.put("/{room_id}", response_model=RoomRead)
def update_room(
    room_id: uuid.UUID,
    payload: RoomUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.national_admin,
            UserRole.district_admin,
        )
    ),
):
    room = get_room_in_scope(db, user, room_id)

    values = payload.model_dump(exclude_unset=True)

    for key, value in values.items():
        setattr(room, key, value)

    if room.status == RoomStatus.occupied:
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

    db.commit()
    db.refresh(room)

    return room


@router.delete("/{room_id}")
def delete_room(
    room_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin, UserRole.district_admin)),
):
    room = get_room_in_scope(db, user, room_id)

    active_occupancy = (
        db.query(Occupancy)
        .filter(
            Occupancy.room_id == room.id,
            Occupancy.status == OccupancyStatus.active,
        )
        .first()
    )

    if active_occupancy:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Move out the tenant before deleting this occupied room.",
        )

    (
        db.query(RoomListing)
        .filter(RoomListing.room_id == room.id)
        .update(
            {
                "status": ListingStatus.archived,
                "is_public": False,
            }
        )
    )

    db.delete(room)
    db.commit()

    return {"detail": "Room deleted"}
