from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    Occupancy,
    OccupancyStatus,
    RentDue,
    RentDueStatus,
    Room,
    RoomStatus,
)


def money(value) -> Decimal:
    return Decimal(value or 0)


def calculate_landlord_revenue(
    db: Session,
    landlord_id,
) -> dict:
    dues = (
        db.query(RentDue)
        .filter(RentDue.landlord_id == landlord_id)
        .all()
    )

    total_expected = sum((money(due.amount_due) for due in dues), Decimal("0"))
    total_collected = sum((money(due.amount_paid) for due in dues), Decimal("0"))
    total_outstanding = total_expected - total_collected

    return {
        "total_expected": total_expected,
        "total_collected": total_collected,
        "total_outstanding": total_outstanding,
    }


def calculate_overdue_exposure(
    db: Session,
    landlord_id,
) -> dict:
    overdue_dues = (
        db.query(RentDue)
        .filter(
            RentDue.landlord_id == landlord_id,
            RentDue.status == RentDueStatus.overdue,
        )
        .all()
    )

    overdue_amount = sum(
        (money(due.amount_due) - money(due.amount_paid) for due in overdue_dues),
        Decimal("0"),
    )

    return {
        "overdue_count": len(overdue_dues),
        "overdue_amount": overdue_amount,
    }


def calculate_occupancy_rate(
    db: Session,
    landlord_id,
) -> dict:
    rooms = (
        db.query(Room)
        .filter(Room.landlord_id == landlord_id)
        .all()
    )

    total_slots = sum((room.occupancy_limit or 1) for room in rooms)

    active_occupancies = (
        db.query(Occupancy)
        .filter(
            Occupancy.landlord_id == landlord_id,
            Occupancy.status == OccupancyStatus.active,
        )
        .count()
    )

    occupancy_rate = 0

    if total_slots > 0:
        occupancy_rate = round((active_occupancies / total_slots) * 100, 2)

    return {
        "total_rooms": len(rooms),
        "total_slots": total_slots,
        "active_occupancies": active_occupancies,
        "occupancy_rate": occupancy_rate,
    }


def calculate_collection_rate(
    db: Session,
    landlord_id,
) -> dict:
    revenue = calculate_landlord_revenue(db, landlord_id)

    total_expected = money(revenue["total_expected"])
    total_collected = money(revenue["total_collected"])

    collection_rate = 0

    if total_expected > 0:
        collection_rate = round(float((total_collected / total_expected) * 100), 2)

    return {
        "collection_rate": collection_rate,
    }


def calculate_room_status_summary(
    db: Session,
    landlord_id,
) -> dict:
    rooms = (
        db.query(Room)
        .filter(Room.landlord_id == landlord_id)
        .all()
    )

    return {
        "vacant": sum(1 for room in rooms if room.status == RoomStatus.vacant),
        "occupied": sum(1 for room in rooms if room.status == RoomStatus.occupied),
        "partially_occupied": sum(
            1 for room in rooms if room.status == RoomStatus.partially_occupied
        ),
        "full": sum(1 for room in rooms if room.status == RoomStatus.full),
        "maintenance": sum(
            1 for room in rooms if room.status == RoomStatus.maintenance
        ),
        "reserved": sum(1 for room in rooms if room.status == RoomStatus.reserved),
    }


def calculate_property_financial_summary(
    db: Session,
    landlord_id,
) -> dict:
    revenue = calculate_landlord_revenue(db, landlord_id)
    overdue = calculate_overdue_exposure(db, landlord_id)
    occupancy = calculate_occupancy_rate(db, landlord_id)
    collection = calculate_collection_rate(db, landlord_id)
    rooms = calculate_room_status_summary(db, landlord_id)

    return {
        **revenue,
        **overdue,
        **occupancy,
        **collection,
        "rooms": rooms,
    }
