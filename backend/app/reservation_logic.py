import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.audit import log_action
from app.models import (
    AuditAction,
    ListingStatus,
    Notification,
    PaymentReceipt,
    PaymentTransaction,
    PaymentTransactionStatus,
    PaymentType,
    Landlord,
    Room,
    RoomListing,
    RoomReservation,
    RoomReservationStatus,
    RoomStatus,
)


ACTIVE_RESERVATION_STATUSES = {
    RoomReservationStatus.pending_landlord_review,
    RoomReservationStatus.approved_for_payment,
    RoomReservationStatus.payment_pending,
    RoomReservationStatus.confirmed,
}


def next_reservation_code(db: Session) -> str:
    sequence = db.query(RoomReservation).count() + 1
    while True:
        code = f"RL-RES-{sequence:06d}"
        if not db.query(RoomReservation).filter(RoomReservation.reservation_code == code).first():
            return code
        sequence += 1


def serialize_reservation(reservation: RoomReservation) -> dict:
    return {
        "id": reservation.id,
        "room_id": reservation.room_id,
        "property_id": reservation.property_id,
        "room_seeker_id": reservation.room_seeker_id,
        "landlord_id": reservation.landlord_id,
        "application_id": reservation.application_id,
        "payment_id": reservation.payment_id,
        "reservation_code": reservation.reservation_code,
        "status": reservation.status,
        "reservation_amount": float(reservation.reservation_amount or 0),
        "reservation_expiry": reservation.reservation_expiry,
        "rejection_message": visible_rejection_message(reservation),
        "rejection_expires_at": reservation.rejection_expires_at,
        "full_name": reservation.full_name,
        "phone": reservation.phone,
        "email": reservation.email,
        "message": reservation.message,
        "created_at": reservation.created_at,
        "updated_at": reservation.updated_at,
        "room_number": reservation.room.room_number if reservation.room else None,
        "property_name": reservation.property.name if reservation.property else None,
    }


def get_active_reservation_for_room(db: Session, room_id: uuid.UUID) -> RoomReservation | None:
    return (
        db.query(RoomReservation)
        .filter(RoomReservation.room_id == room_id, RoomReservation.status.in_(ACTIVE_RESERVATION_STATUSES))
        .order_by(RoomReservation.created_at.desc())
        .first()
    )


def assert_room_can_receive_reservation(db: Session, room: Room, exclude_reservation_id: uuid.UUID | None = None) -> None:
    if room.status != RoomStatus.vacant:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is no longer available.")
    active = get_active_reservation_for_room(db, room.id)
    if active and active.id != exclude_reservation_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room already has an active reservation request.")


def expire_stale_reservations(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    stale = (
        db.query(RoomReservation)
        .filter(
            RoomReservation.status.in_(
                {
                    RoomReservationStatus.pending_landlord_review,
                    RoomReservationStatus.approved_for_payment,
                    RoomReservationStatus.payment_pending,
                }
            ),
            RoomReservation.reservation_expiry.is_not(None),
            RoomReservation.reservation_expiry < now,
        )
        .all()
    )
    for reservation in stale:
        reservation.status = RoomReservationStatus.expired
    return len(stale)


def visible_rejection_message(reservation: RoomReservation) -> str | None:
    if not reservation.rejection_message:
        return None
    if not reservation.rejection_expires_at:
        return reservation.rejection_message
    expires_at = reservation.rejection_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return reservation.rejection_message if expires_at > datetime.now(timezone.utc) else None


def clear_expired_rejection_messages(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    return (
        db.query(RoomReservation)
        .filter(
            RoomReservation.rejection_message.is_not(None),
            RoomReservation.rejection_expires_at.is_not(None),
            RoomReservation.rejection_expires_at < now,
        )
        .update({RoomReservation.rejection_message: None}, synchronize_session=False)
    )


def complete_room_reservation_payment(db: Session, transaction: PaymentTransaction, receipt_number: str) -> None:
    reservation = db.get(RoomReservation, transaction.room_reservation_id) if transaction.room_reservation_id else None
    if not reservation:
        transaction.status = PaymentTransactionStatus.failed
        transaction.failure_reason = "Reservation was not found for successful payment"
        return
    if reservation.status not in {RoomReservationStatus.payment_pending, RoomReservationStatus.approved_for_payment}:
        transaction.status = PaymentTransactionStatus.failed
        transaction.failure_reason = f"Reservation is not payable from {reservation.status.value}"
        return
    room = db.get(Room, reservation.room_id)
    if not room or room.status != RoomStatus.vacant:
        transaction.status = PaymentTransactionStatus.failed
        transaction.failure_reason = "Room is no longer available for reservation confirmation"
        return
    existing_confirmed = (
        db.query(RoomReservation)
        .filter(
            RoomReservation.room_id == reservation.room_id,
            RoomReservation.id != reservation.id,
            RoomReservation.status.in_({RoomReservationStatus.confirmed, RoomReservationStatus.completed}),
        )
        .first()
    )
    if existing_confirmed:
        transaction.status = PaymentTransactionStatus.failed
        transaction.failure_reason = "Room already has a confirmed reservation"
        return
    reservation.status = RoomReservationStatus.confirmed
    reservation.payment_id = transaction.id
    room.status = RoomStatus.reserved
    db.query(RoomListing).filter(RoomListing.room_id == room.id).update(
        {RoomListing.is_public: False, RoomListing.status: ListingStatus.rented},
        synchronize_session=False,
    )
    receipt = PaymentReceipt(
        landlord_id=reservation.landlord_id,
        tenant_id=None,
        room_id=reservation.room_id,
        room_reservation_id=reservation.id,
        receipt_type=PaymentType.room_reservation.value,
        receipt_number=receipt_number,
        amount=transaction.amount,
        method=transaction.method,
        transaction_reference=transaction.provider_reference or transaction.idempotency_key,
        pdf_url=f"/payments/transactions/{transaction.id}/receipt",
    )
    db.add(receipt)
    landlord = db.get(Landlord, reservation.landlord_id)
    if landlord:
        db.add(
            Notification(
                user_id=landlord.user_id,
                title="Room reservation confirmed",
                body=f"Reservation {reservation.reservation_code} was confirmed after payment.",
                category="reservations",
            )
        )
    log_action(db, AuditAction.create_payment, None, reservation.landlord_id, "RoomReservation", reservation.id)


def default_reservation_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=2)
