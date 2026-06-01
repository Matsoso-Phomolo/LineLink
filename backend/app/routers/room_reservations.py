import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit import log_action
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import (
    ApplicationStatus,
    AuditAction,
    Landlord,
    Notification,
    PaymentMethod,
    PaymentTransaction,
    PaymentTransactionStatus,
    PaymentType,
    PreferredResponseMethod,
    Room,
    RoomListing,
    RoomReservation,
    RoomReservationStatus,
    TenantApplication,
    TenantType,
    User,
    UserRole,
)
from app.ownership import landlord_scope_filter
from app.payment_providers.base import PaymentProviderRequest
from app.reservation_logic import (
    assert_room_can_receive_reservation,
    default_reservation_expiry,
    expire_stale_reservations,
    next_reservation_code,
    serialize_reservation,
)
from app.routers.payments import PROVIDERS
from app.routers.public_listings import get_public_listing, validate_response_method
from app.schemas import (
    PaymentInitiateResponse,
    RoomReservationDecision,
    RoomReservationPayRequest,
    RoomReservationRead,
    RoomReservationRequestCreate,
)

router = APIRouter(prefix="/room-reservations", tags=["room reservations"])
landlord_router = APIRouter(prefix="/landlord/reservations", tags=["landlord reservations"])
admin_router = APIRouter(prefix="/admin/room-reservations", tags=["admin room reservations"])


def get_reservation_or_404(db: Session, reservation_id: uuid.UUID) -> RoomReservation:
    reservation = db.get(RoomReservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room reservation not found")
    return reservation


def ensure_landlord_reservation_scope(db: Session, user: User, reservation: RoomReservation) -> None:
    if user.role == UserRole.admin:
        return
    scoped = landlord_scope_filter(db, user, RoomReservation).filter(RoomReservation.id == reservation.id).first()
    if not scoped:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reservation is outside your landlord scope")


def create_reservation_from_listing(
    db: Session,
    listing: RoomListing,
    payload: RoomReservationRequestCreate,
) -> RoomReservation:
    room = db.get(Room, listing.room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is no longer available.")
    assert_room_can_receive_reservation(db, room)
    application = TenantApplication(
        listing_id=listing.id,
        room_id=listing.room_id,
        property_id=listing.property_id,
        landlord_id=listing.landlord_id,
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        tenant_type=TenantType.non_student,
        message=payload.message,
        preferred_response_method=payload.preferred_response_method,
        response_contact_value=payload.email if payload.preferred_response_method == PreferredResponseMethod.email else payload.phone,
        status=ApplicationStatus.inquiry_pending,
    )
    db.add(application)
    db.flush()
    reservation = RoomReservation(
        room_id=listing.room_id,
        property_id=listing.property_id,
        landlord_id=listing.landlord_id,
        application_id=application.id,
        reservation_code=next_reservation_code(db),
        status=RoomReservationStatus.pending_landlord_review,
        reservation_amount=listing.deposit_amount or listing.rent_price,
        reservation_expiry=default_reservation_expiry(),
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        message=payload.message,
    )
    db.add(reservation)
    landlord = db.get(Landlord, listing.landlord_id)
    if landlord:
        db.add(
            Notification(
                user_id=landlord.user_id,
                title="New reservation request",
                body=f"{payload.full_name} requested to reserve {listing.title}. Review before allowing deposit payment.",
                category="reservations",
            )
        )
    return reservation


@router.post("/request", response_model=RoomReservationRead)
def request_room_reservation(payload: RoomReservationRequestCreate, db: Session = Depends(get_db)):
    expire_stale_reservations(db)
    listing = get_public_listing(db, payload.listing_id)
    validate_response_method(payload)
    reservation = create_reservation_from_listing(db, listing, payload)
    db.commit()
    db.refresh(reservation)
    return serialize_reservation(reservation)


@router.get("/my-reservations", response_model=list[RoomReservationRead])
def my_reservations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(RoomReservation).filter(RoomReservation.room_seeker_id == user.id).order_by(RoomReservation.created_at.desc()).all()
    return [serialize_reservation(item) for item in items]


@router.get("/{reservation_id}", response_model=RoomReservationRead)
def get_public_reservation_status(reservation_id: uuid.UUID, db: Session = Depends(get_db)):
    expire_stale_reservations(db)
    reservation = get_reservation_or_404(db, reservation_id)
    db.commit()
    db.refresh(reservation)
    return serialize_reservation(reservation)


@router.post("/{reservation_id}/pay", response_model=PaymentInitiateResponse)
def pay_room_reservation(reservation_id: uuid.UUID, payload: RoomReservationPayRequest, db: Session = Depends(get_db)):
    expire_stale_reservations(db)
    reservation = get_reservation_or_404(db, reservation_id)
    if reservation.status != RoomReservationStatus.approved_for_payment:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Landlord approval is required before deposit payment.")
    if payload.method not in PROVIDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported payment method")
    if payload.method in {PaymentMethod.mpesa, PaymentMethod.ecocash, PaymentMethod.mopay_mpesa, PaymentMethod.mopay_ecocash} and not payload.payer_phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number is required for mobile money payments")
    amount = float(reservation.reservation_amount or 0)
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Landlord must set a payment amount before payment can start.")
    idempotency_key = payload.idempotency_key or f"reservation-{reservation.id}-{payload.method.value}-{amount}"
    existing = db.query(PaymentTransaction).filter(PaymentTransaction.idempotency_key == idempotency_key).first()
    if existing:
        return existing
    transaction = PaymentTransaction(
        landlord_id=reservation.landlord_id,
        tenant_id=None,
        rent_due_id=None,
        room_reservation_id=reservation.id,
        amount=amount,
        method=payload.method,
        payer_phone=payload.payer_phone,
        payment_type=PaymentType.room_reservation.value,
        idempotency_key=idempotency_key,
        status=PaymentTransactionStatus.pending_verification if payload.method in {PaymentMethod.bank, PaymentMethod.bank_transfer} else PaymentTransactionStatus.pending,
    )
    db.add(transaction)
    db.flush()
    result = PROVIDERS[payload.method].initiate(PaymentProviderRequest(transaction.id, float(amount), payload.payer_phone, idempotency_key))
    transaction.checkout_request_id = result.checkout_request_id
    transaction.provider_reference = result.provider_reference
    transaction.provider_message = result.message
    reservation.status = RoomReservationStatus.payment_pending
    reservation.payment_id = transaction.id
    log_action(db, AuditAction.create_payment, None, reservation.landlord_id, "RoomReservation", reservation.id)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/{reservation_id}/cancel", response_model=RoomReservationRead)
def cancel_room_reservation(reservation_id: uuid.UUID, db: Session = Depends(get_db)):
    reservation = get_reservation_or_404(db, reservation_id)
    if reservation.status in {RoomReservationStatus.confirmed, RoomReservationStatus.completed}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Confirmed reservations cannot be cancelled here.")
    reservation.status = RoomReservationStatus.cancelled
    db.commit()
    db.refresh(reservation)
    return serialize_reservation(reservation)


@landlord_router.get("", response_model=list[RoomReservationRead])
def landlord_reservations(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    expire_stale_reservations(db)
    query = landlord_scope_filter(db, user, RoomReservation).order_by(RoomReservation.created_at.desc())
    items = query.all()
    db.commit()
    return [serialize_reservation(item) for item in items]


@landlord_router.post("/{reservation_id}/approve-payment", response_model=RoomReservationRead)
def approve_reservation_payment(reservation_id: uuid.UUID, payload: RoomReservationDecision, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    reservation = get_reservation_or_404(db, reservation_id)
    ensure_landlord_reservation_scope(db, user, reservation)
    if reservation.status != RoomReservationStatus.pending_landlord_review:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending requests can be approved for payment.")
    if payload.amount is None or payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Payment amount must be greater than 0.")
    room = db.get(Room, reservation.room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    assert_room_can_receive_reservation(db, room, reservation.id)
    reservation.reservation_amount = payload.amount
    reservation.status = RoomReservationStatus.approved_for_payment
    reservation.rejection_message = None
    reservation.rejection_expires_at = None
    if reservation.application_id:
        application = db.get(TenantApplication, reservation.application_id)
        if application:
            application.status = ApplicationStatus.accepted
            application.landlord_note = payload.note
    db.add(Notification(user_id=user.id, title="Reservation approved for payment", body=f"{reservation.reservation_code} can now pay the room deposit.", category="reservations"))
    log_action(db, AuditAction.update_room_listing, user, reservation.landlord_id, "RoomReservation", reservation.id)
    db.commit()
    db.refresh(reservation)
    return serialize_reservation(reservation)


@landlord_router.post("/{reservation_id}/reject", response_model=RoomReservationRead)
def reject_reservation(reservation_id: uuid.UUID, payload: RoomReservationDecision, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    reservation = get_reservation_or_404(db, reservation_id)
    ensure_landlord_reservation_scope(db, user, reservation)
    if reservation.status in {RoomReservationStatus.confirmed, RoomReservationStatus.completed}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Confirmed reservations cannot be rejected.")
    previous_status = reservation.status
    reservation.status = RoomReservationStatus.cancelled if previous_status in {RoomReservationStatus.approved_for_payment, RoomReservationStatus.payment_pending} else RoomReservationStatus.rejected
    reservation.rejection_message = payload.note or "This reservation request was not accepted."
    reservation.rejection_expires_at = datetime.now(timezone.utc) + timedelta(minutes=60)
    if reservation.application_id:
        application = db.get(TenantApplication, reservation.application_id)
        if application:
            application.status = ApplicationStatus.rejected
            application.landlord_note = payload.note
    log_action(db, AuditAction.update_room_listing, user, reservation.landlord_id, "RoomReservation", reservation.id)
    db.commit()
    db.refresh(reservation)
    return serialize_reservation(reservation)


@admin_router.get("", response_model=list[RoomReservationRead])
def admin_room_reservations(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    return [serialize_reservation(item) for item in db.query(RoomReservation).order_by(RoomReservation.created_at.desc()).limit(500).all()]
