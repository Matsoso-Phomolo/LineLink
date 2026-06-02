import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import (
    ListingStatus,
    Occupancy,
    OccupancyStatus,
    Room,
    RoomListing,
    RoomReservation,
    RoomReservationStatus,
    RoomStatus,
    User,
    UserRole,
)
from app.ownership import get_property_in_scope, get_room_in_scope, scoped_query
from app.schemas import RoomCreate, RoomRead, RoomUpdate

router = APIRouter(prefix="/rooms", tags=["rooms"])


class RoomStatusUpdate(BaseModel):
    status: RoomStatus


def normalize_room_status(raw_status: object) -> str:
    value = str(raw_status or "").strip().lower()
    return value if value in {item.value for item in RoomStatus} else RoomStatus.vacant.value


def normalize_room_type(raw_type: object) -> str:
    value = str(raw_type or "").strip().lower()
    return value if value in {"single", "double", "multiple"} else "single"


def room_scope_sql(user: User) -> tuple[str, dict[str, object]]:
    if user.role == UserRole.national_admin:
        return "", {}

    if user.role == UserRole.landlord and user.landlord_profile:
        return "where r.landlord_id = :landlord_id", {
            "landlord_id": user.landlord_profile.id,
        }

    if user.role == UserRole.caretaker and user.caretaker_profile:
        return "where r.landlord_id = :landlord_id", {
            "landlord_id": user.caretaker_profile.landlord_id,
        }

    if user.role == UserRole.district_admin:
        return (
            """
            where exists (
                select 1
                from properties p
                join district_admin_assignments daa
                    on daa.district_id = p.district_id
                where p.id = r.property_id
                and daa.user_id = :user_id
                and daa.is_active is true
            )
            """,
            {"user_id": user.id},
        )

    return "where false", {}


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
    where_sql, params = room_scope_sql(user)
    rows = (
        db.execute(
            text(
                f"""
                select
                    r.id,
                    r.landlord_id,
                    r.property_id,
                    r.category_id,
                    r.room_number,
                    r.status::text as status,
                    r.room_type::text as room_type,
                    r.room_size,
                    r.rent_price,
                    r.deposit_amount,
                    r.notes,
                    r.created_at
        from rooms r
        left join properties p on p.id = r.property_id
        {where_sql}
        order by
                    p.name,
                    case r.room_type::text
                        when 'single' then 0
                        when 'double' then 1
                        else 2
                    end,
                    regexp_replace(r.room_number, '\\d.*$', ''),
                    nullif(regexp_replace(r.room_number, '\\D', '', 'g'), '')::int,
                    r.room_number
                """
            ),
            params,
        )
        .mappings()
        .all()
    )

    return [
        {
            **dict(row),
            "status": normalize_room_status(row.get("status")),
            "room_type": normalize_room_type(row.get("room_type")),
        }
        for row in rows
    ]


@router.patch("/{room_id}/status", response_model=RoomRead)
def update_room_status(
    room_id: uuid.UUID,
    payload: RoomStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker)),
):
    room = get_room_in_scope(db, user, room_id)
    next_status = payload.status

    active_occupancy = (
        db.query(Occupancy)
        .filter(
            Occupancy.room_id == room.id,
            Occupancy.status == OccupancyStatus.active,
        )
        .first()
    )

    if next_status == RoomStatus.vacant and active_occupancy:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="End the active tenant or lease before marking this room vacant.",
        )

    confirmed_reservation = (
        db.query(RoomReservation)
        .filter(
            RoomReservation.room_id == room.id,
            RoomReservation.status == RoomReservationStatus.confirmed,
        )
        .first()
    )

    if next_status == RoomStatus.vacant and confirmed_reservation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancel or expire the confirmed reservation before marking this room vacant.",
        )

    room.status = next_status

    if next_status != RoomStatus.vacant:
        listing_status = ListingStatus.rented if next_status == RoomStatus.occupied else ListingStatus.archived
        (
            db.query(RoomListing)
            .filter(
                RoomListing.room_id == room.id,
                RoomListing.status == ListingStatus.published,
            )
            .update(
                {
                    "status": listing_status,
                    "is_public": False,
                }
            )
        )

    db.commit()
    db.refresh(room)

    return room


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
