import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Occupancy, OccupancyMode, OccupancyStatus, Room, RoomStatus


BLOCKING_ROOM_STATUSES = {RoomStatus.maintenance}


@dataclass(frozen=True)
class RoomCapacity:
    room_id: uuid.UUID
    room_number: str
    occupancy_mode: str
    max_occupants: int
    current_occupants_count: int
    available_slots: int
    status: str


@dataclass(frozen=True)
class PropertyTenantCapacity:
    total_rooms: int
    total_account_capacity: int
    used_tenant_accounts: int
    remaining_tenant_accounts: int
    room_breakdown: list[RoomCapacity]


def room_max_occupants(room: Room) -> int:
    max_occupants = int(room.max_occupants or 1)
    if room.occupancy_mode == OccupancyMode.private:
        return 1
    return max(max_occupants, 2)


def active_occupancy_count(db: Session, room_id: uuid.UUID) -> int:
    return (
        db.query(Occupancy)
        .filter(
            Occupancy.room_id == room_id,
            Occupancy.status == OccupancyStatus.active,
            Occupancy.is_active.is_(True),
        )
        .count()
    )


def room_available_slots(db: Session, room: Room) -> int:
    if room.status in BLOCKING_ROOM_STATUSES:
        return 0
    return max(room_max_occupants(room) - active_occupancy_count(db, room.id), 0)


def room_capacity_status(db: Session, room: Room) -> RoomStatus:
    if room.status == RoomStatus.maintenance:
        return RoomStatus.maintenance
    count = active_occupancy_count(db, room.id)
    max_occupants = room_max_occupants(room)
    if count <= 0:
        return RoomStatus.vacant
    if room.occupancy_mode == OccupancyMode.shared_independent and count < max_occupants:
        return RoomStatus.partially_occupied
    return RoomStatus.occupied


def sync_room_capacity_status(db: Session, room: Room) -> RoomStatus:
    next_status = room_capacity_status(db, room)
    room.status = next_status
    return next_status


def calculate_property_tenant_capacity(db: Session, property_id: uuid.UUID) -> PropertyTenantCapacity:
    rooms = (
        db.query(Room)
        .filter(Room.property_id == property_id)
        .order_by(Room.room_type, Room.room_number)
        .all()
    )
    breakdown: list[RoomCapacity] = []
    total_capacity = 0
    used_accounts = 0

    for room in rooms:
        max_occupants = room_max_occupants(room)
        current = active_occupancy_count(db, room.id)
        available = 0 if room.status in BLOCKING_ROOM_STATUSES else max(max_occupants - current, 0)
        status_value = room_capacity_status(db, room).value
        total_capacity += max_occupants
        used_accounts += current
        breakdown.append(
            RoomCapacity(
                room_id=room.id,
                room_number=room.room_number,
                occupancy_mode=room.occupancy_mode.value,
                max_occupants=max_occupants,
                current_occupants_count=current,
                available_slots=available,
                status=status_value,
            )
        )

    return PropertyTenantCapacity(
        total_rooms=len(rooms),
        total_account_capacity=total_capacity,
        used_tenant_accounts=used_accounts,
        remaining_tenant_accounts=max(total_capacity - used_accounts, 0),
        room_breakdown=breakdown,
    )


def next_available_slot(db: Session, room: Room) -> int:
    max_occupants = room_max_occupants(room)
    used_slots = {
        slot
        for (slot,) in db.query(Occupancy.occupancy_slot_number)
        .filter(
            Occupancy.room_id == room.id,
            Occupancy.status == OccupancyStatus.active,
            Occupancy.is_active.is_(True),
        )
        .all()
    }
    for slot in range(1, max_occupants + 1):
        if slot not in used_slots:
            return slot
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Room is full. No tenant account slots are available.",
    )


def validate_room_can_accept_tenant(db: Session, room: Room) -> int:
    if room.status in BLOCKING_ROOM_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Maintenance rooms cannot accept tenants.",
        )
    if room_available_slots(db, room) <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room is full. No tenant account slots are available.",
        )
    return next_available_slot(db, room)


def end_occupancy(occupancy: Occupancy) -> None:
    occupancy.status = OccupancyStatus.ended
    occupancy.is_active = False
    occupancy.ended_at = datetime.now(timezone.utc)
