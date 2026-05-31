import logging
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.audit import log_action
from app.database import get_db
from app.dependencies import (
    get_district_admin_district_ids,
    is_district_admin,
    is_national_admin,
    require_roles,
)
from app.identity import next_identifier
from app.models import (
    AuditAction,
    Landlord,
    LandlordRequest,
    LandlordRequestProperty,
    LandlordRequestStatus,
    LandlordVerification,
    PreferredResponseMethod,
    Property,
    PropertySubscription,
    Room,
    SubscriptionStatus,
    User,
    UserRole,
)
from app.schemas import (
    LandlordCreate,
    LandlordManualCreate,
    LandlordOnboardingResult,
    LandlordRead,
    LandlordRequestCreate,
    LandlordRequestDecision,
    LandlordRequestRead,
    LandlordVerificationCreate,
    LandlordVerificationReview,
)
from app.services.room_generation_service import generate_room_numbers
from app.subscription_rules import calculate_property_subscription_amount

router = APIRouter(prefix="/landlords", tags=["landlords"])
logger = logging.getLogger(__name__)

NIL_UUID = "00000000-0000-0000-0000-000000000000"


def normalize_request_status(raw_status: object) -> LandlordRequestStatus:
    value = str(raw_status or "").strip().lower()

    for item in LandlordRequestStatus:
        if value == item.value:
            return item

    legacy_statuses = {
        "active": LandlordRequestStatus.approved,
        "disabled": LandlordRequestStatus.rejected,
        "pending_verification": LandlordRequestStatus.verification_requested,
        "under-review": LandlordRequestStatus.under_review,
        "review": LandlordRequestStatus.under_review,
        "submitted": LandlordRequestStatus.verification_submitted,
        "verified": LandlordRequestStatus.ai_reviewed,
        "accepted": LandlordRequestStatus.approved,
        "declined": LandlordRequestStatus.rejected,
    }

    normalized = legacy_statuses.get(value, LandlordRequestStatus.pending)
    logger.warning(
        "Normalized malformed landlord request status",
        extra={"raw_status": raw_status, "normalized_status": normalized.value},
    )
    return normalized


def normalize_response_method(raw_method: object) -> PreferredResponseMethod:
    value = str(raw_method or "").strip().lower()

    for item in PreferredResponseMethod:
        if value == item.value:
            return item

    logger.warning(
        "Normalized malformed landlord request response method",
        extra={"raw_method": raw_method},
    )
    return PreferredResponseMethod.email


def safe_positive_int(value: object, fallback: int = 1) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else fallback
    except (TypeError, ValueError):
        return fallback


def safe_non_negative_int(value: object, fallback: int = 0) -> int:
    try:
        parsed = int(value)
        return parsed if parsed >= 0 else fallback
    except (TypeError, ValueError):
        return fallback


def safe_email(value: object, request_id: object) -> str:
    email = str(value or "").strip()

    if "@" in email and "." in email.split("@")[-1]:
        return email

    return f"landlord-request-{request_id}@rentalink.local"


def serialize_landlord_request_property(row: dict[str, object]) -> dict[str, object] | None:
    request_id = row.get("landlord_request_id")
    property_id = row.get("id")

    try:
        total_rooms = safe_positive_int(row.get("total_rooms"))
        single_rooms = safe_non_negative_int(row.get("single_rooms"))
        double_rooms = safe_non_negative_int(row.get("double_rooms"))

        if single_rooms + double_rooms != total_rooms:
            if single_rooms == 0 and double_rooms == 0:
                single_rooms = total_rooms
            else:
                logger.warning(
                    "Normalized malformed landlord request property room counts",
                    extra={
                        "landlord_request_id": str(request_id),
                        "landlord_request_property_id": str(property_id),
                        "total_rooms": total_rooms,
                        "single_rooms": single_rooms,
                        "double_rooms": double_rooms,
                    },
                )
                total_rooms = max(total_rooms, single_rooms + double_rooms, 1)

        return {
            "id": str(property_id),
            "landlord_request_id": str(request_id),
            "property_name": row.get("property_name")
            or row.get("business_name")
            or "Unspecified property",
            "district_id": str(row.get("district_id") or NIL_UUID),
            "area_id": str(row.get("area_id") or NIL_UUID),
            "village_location": row.get("village_location")
            or row.get("location_area")
            or "Unspecified location",
            "address": row.get("address") or "Address pending verification",
            "description": row.get("description"),
            "total_rooms": total_rooms,
            "single_rooms": single_rooms,
            "double_rooms": double_rooms,
            "single_room_prefix": row.get("single_room_prefix") or "A",
            "double_room_prefix": row.get("double_room_prefix") or "B",
            "starting_room_number": safe_positive_int(
                row.get("starting_room_number"),
                fallback=101,
            ),
            "single_room_rent": row.get("single_room_rent"),
            "double_room_rent": row.get("double_room_rent"),
            "created_at": row.get("created_at") or datetime.now(timezone.utc),
        }
    except Exception:
        logger.exception(
            "Skipped malformed landlord request property row",
            extra={
                "landlord_request_id": str(request_id),
                "landlord_request_property_id": str(property_id),
            },
        )
        return None


def serialize_landlord_request_row(
    row: dict[str, object],
    properties_by_request_id: dict[str, list[dict[str, object]]],
) -> dict[str, object] | None:
    request_id = row.get("id")

    try:
        full_name = str(
            row.get("full_name")
            or row.get("business_name")
            or row.get("email")
            or "Unknown landlord"
        ).strip()
        email = safe_email(row.get("email"), request_id)
        phone = str(row.get("phone") or "").strip() or None
        address = str(row.get("address") or row.get("physical_address") or "").strip()
        response_method = normalize_response_method(
            row.get("preferred_response_method")
        )
        response_contact_value = (
            str(row.get("response_contact_value") or "").strip()
            or (email if response_method == PreferredResponseMethod.email else phone)
            or email
        )

        serialized = {
            "id": str(request_id),
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "address": address or "Address pending verification",
            "preferred_response_method": response_method.value,
            "response_contact_value": response_contact_value,
            "emergency_contact": row.get("emergency_contact"),
            "message": row.get("message"),
            "status": normalize_request_status(row.get("status")).value,
            "admin_note": row.get("admin_note"),
            "landlord_id": str(row["landlord_id"]) if row.get("landlord_id") else None,
            "approved_by_user_id": (
                str(row["approved_by_user_id"])
                if row.get("approved_by_user_id")
                else None
            ),
            "approved_at": row.get("approved_at"),
            "created_at": row.get("created_at") or datetime.now(timezone.utc),
            "properties": properties_by_request_id.get(str(request_id), []),
        }

        logger.info(
            "Serialized landlord request row",
            extra={
                "landlord_request_id": str(request_id),
                "status": serialized["status"],
                "properties_count": len(serialized["properties"]),
            },
        )
        return serialized
    except Exception:
        logger.exception(
            "Skipped malformed landlord request row",
            extra={"landlord_request_id": str(request_id)},
        )
        return None


def generate_landlord_number(db: Session) -> str:
    sequence = db.query(Landlord).count() + 1

    while True:
        number = f"LL-LND-{sequence:06d}"

        if not db.query(Landlord).filter(
            Landlord.system_landlord_number == number
        ).first():
            return number

        sequence += 1


def generated_password() -> str:
    return f"LL-{secrets.token_urlsafe(10)}aA1!"


def ensure_landlord_numbers(db: Session) -> None:
    changed = False

    landlords = (
        db.query(Landlord)
        .filter(Landlord.system_landlord_number.is_(None))
        .order_by(Landlord.created_at.asc())
        .all()
    )

    for landlord in landlords:
        landlord.system_landlord_number = generate_landlord_number(db)
        changed = True

    if changed:
        db.commit()


def create_landlord_account(
    db: Session,
    *,
    full_name: str,
    email: str,
    phone: str | None,
    address: str | None,
    password: str,
) -> Landlord:
    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user and existing_user.role != UserRole.landlord:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already belongs to a non-landlord account",
        )

    user = existing_user

    if not user:
        user = User(
            username=next_identifier(db, UserRole.landlord),
            email=email,
            phone=phone,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role=UserRole.landlord,
            is_active=True,
            must_change_password=True,
        )

        db.add(user)
        db.flush()

    user.is_active = True
    user.must_change_password = True

    landlord = db.query(Landlord).filter(
        Landlord.user_id == user.id
    ).first()

    if landlord:
        landlord.business_name = full_name
        landlord.contact_phone = phone
        landlord.email = email
        landlord.address = address
        landlord.is_active = True

        if not landlord.system_landlord_number:
            landlord.system_landlord_number = generate_landlord_number(db)

        user.username = landlord.system_landlord_number

        return landlord

    landlord = Landlord(
        user_id=user.id,
        business_name=full_name,
        contact_phone=phone,
        email=email,
        address=address,
        system_landlord_number=generate_landlord_number(db),
        is_active=True,
    )

    db.add(landlord)
    db.flush()

    user.username = landlord.system_landlord_number

    return landlord


@router.post(
    "/requests",
    response_model=LandlordRequestRead,
)
def create_landlord_request(
    payload: LandlordRequestCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(LandlordRequest)
        .filter(
            LandlordRequest.email == payload.email,
            LandlordRequest.status == LandlordRequestStatus.pending,
        )
        .first()
    )

    if existing:
        return existing

    request = LandlordRequest(
        **payload.model_dump(),
        status=LandlordRequestStatus.pending,
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    return request


@router.get(
    "/requests",
    response_model=list[LandlordRequestRead],
)
def list_landlord_requests(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    try:
        request_rows = [
            dict(row)
            for row in db.execute(
                text(
                    """
                    select
                        id,
                        business_name,
                        full_name,
                        email,
                        phone,
                        address,
                        emergency_contact,
                        message,
                        preferred_response_method::text as preferred_response_method,
                        response_contact_value,
                        status::text as status,
                        admin_note,
                        landlord_id,
                        approved_by_user_id,
                        approved_at,
                        created_at
                    from landlord_requests
                    order by created_at desc
                    """
                )
            )
            .mappings()
            .all()
        ]
    except Exception:
        logger.exception("Failed to load landlord request rows")
        return []

    try:
        property_rows = [
            dict(row)
            for row in db.execute(
                text(
                    """
                    select *
                    from landlord_request_properties
                    order by created_at asc
                    """
                )
            )
            .mappings()
            .all()
        ]
    except Exception:
        logger.exception("Failed to load landlord request property rows")
        property_rows = []

    properties_by_request_id: dict[str, list[dict[str, object]]] = {}
    for row in property_rows:
        serialized_property = serialize_landlord_request_property(row)

        if serialized_property:
            request_key = str(serialized_property["landlord_request_id"])
            properties_by_request_id.setdefault(request_key, []).append(
                serialized_property
            )

    results: list[dict[str, object]] = []
    for row in request_rows:
        serialized_request = serialize_landlord_request_row(
            row,
            properties_by_request_id,
        )

        if serialized_request:
            results.append(serialized_request)

    return results


@router.post(
    "/requests/{request_id}/reject",
    response_model=LandlordRequestRead,
)
def reject_landlord_request(
    request_id: uuid.UUID,
    payload: LandlordRequestDecision,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    request = db.get(LandlordRequest, request_id)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landlord request not found",
        )

    request.status = LandlordRequestStatus.rejected
    request.admin_note = payload.admin_note

    db.commit()
    db.refresh(request)

    return request


@router.post(
    "/requests/{request_id}/request-verification",
    response_model=LandlordRequestRead,
)
def request_landlord_verification(
    request_id: uuid.UUID,
    payload: LandlordRequestDecision,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    request = db.get(LandlordRequest, request_id)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landlord request not found",
        )

    if request.status == LandlordRequestStatus.rejected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rejected request cannot be moved to verification",
        )

    request.status = LandlordRequestStatus.verification_requested
    request.admin_note = payload.admin_note
    request.verification_token = secrets.token_urlsafe(48)
    request.verification_token_expires_at = (
        datetime.now(timezone.utc) + timedelta(days=7)
    )

    db.commit()
    db.refresh(request)

    return request


@router.post(
    "/requests/{request_id}/submit-verification",
    response_model=LandlordRequestRead,
)
def submit_landlord_verification(
    request_id: uuid.UUID,
    payload: LandlordVerificationCreate,
    db: Session = Depends(get_db),
):
    request = db.get(LandlordRequest, request_id)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landlord request not found",
        )

    if request.status != LandlordRequestStatus.verification_requested:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification was not requested for this landlord",
        )

    existing_verification = (
        db.query(LandlordVerification)
        .filter(
            LandlordVerification.landlord_request_id == request.id
        )
        .first()
    )

    if existing_verification:
        db.delete(existing_verification)
        db.flush()

    verification = LandlordVerification(
        landlord_request_id=request.id,
        national_id=payload.national_id,
        selfie_path=payload.selfie_path,
        utility_bill_path=payload.utility_bill_path,
        ownership_document_path=payload.ownership_document_path,
        business_registration_path=payload.business_registration_path,
        additional_notes=payload.additional_notes,
    )

    db.add(verification)
    db.flush()

    db.query(LandlordRequestProperty).filter(
        LandlordRequestProperty.landlord_request_id == request.id
    ).delete()

    for property_payload in payload.properties:
        property_record = LandlordRequestProperty(
            landlord_request_id=request.id,
            property_name=property_payload.property_name,
            district_id=property_payload.district_id,
            area_id=property_payload.area_id,
            village_location=property_payload.village_location,
            address=property_payload.address,
            description=property_payload.description,
            total_rooms=property_payload.total_rooms,
            single_rooms=property_payload.single_rooms,
            double_rooms=property_payload.double_rooms,
            single_room_prefix=property_payload.single_room_prefix,
            double_room_prefix=property_payload.double_room_prefix,
            starting_room_number=property_payload.starting_room_number,
            single_room_rent=property_payload.single_room_rent,
            double_room_rent=property_payload.double_room_rent,
        )

        db.add(property_record)

    request.status = (
        LandlordRequestStatus.verification_submitted
    )

    db.commit()
    db.refresh(request)

    return request


@router.post(
    "/requests/{request_id}/reject-verification",
    response_model=LandlordRequestRead,
)
def reject_landlord_verification(
    request_id: uuid.UUID,
    payload: LandlordVerificationReview,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    request = db.get(LandlordRequest, request_id)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landlord request not found",
        )

    if request.status not in [
        LandlordRequestStatus.verification_submitted,
        LandlordRequestStatus.ai_reviewed,
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification has not been submitted yet",
        )

    request.status = (
        LandlordRequestStatus.verification_requested
    )

    request.admin_note = payload.admin_note

    db.commit()
    db.refresh(request)

    return request


@router.post(
    "/requests/{request_id}/approve-verification",
    response_model=LandlordOnboardingResult,
)
def approve_landlord_verification(
    request_id: uuid.UUID,
    payload: LandlordRequestDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.national_admin)),
):
    request = db.get(LandlordRequest, request_id)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landlord request not found",
        )

    if request.status != (
        LandlordRequestStatus.verification_submitted
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification must be submitted before approval",
        )

    request_properties = (
        db.query(LandlordRequestProperty)
        .filter(
            LandlordRequestProperty.landlord_request_id == request.id
        )
        .all()
    )

    if not request_properties:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No verified properties found for this landlord request",
        )

    password = payload.password or generated_password()

    landlord = create_landlord_account(
        db,
        full_name=request.full_name,
        email=request.email,
        phone=request.phone,
        address=request.address,
        password=password,
    )

    for request_property in request_properties:
        property_record = Property(
            landlord_id=landlord.id,
            district_id=request_property.district_id,
            area_id=request_property.area_id,
            name=request_property.property_name,
            description=request_property.description,
            location_area=request_property.village_location,
            address=request_property.address,
        )

        db.add(property_record)
        db.flush()

        generated_rooms = generate_room_numbers(
            total_rooms=request_property.total_rooms,
            single_rooms=request_property.single_rooms,
            double_rooms=request_property.double_rooms,
            single_room_prefix=request_property.single_room_prefix,
            double_room_prefix=request_property.double_room_prefix,
            starting_room_number=request_property.starting_room_number,
        )

        for generated_room in generated_rooms:
            if generated_room.room_type == "single":
                room_rent = (
                    request_property.single_room_rent or 0
                )
            else:
                room_rent = (
                    request_property.double_room_rent or 0
                )

            room = Room(
                landlord_id=landlord.id,
                property_id=property_record.id,
                room_number=generated_room.room_number,
                room_type=generated_room.room_type,
                status="vacant",
                rent_price=room_rent,
                deposit_amount=room_rent,
            )

            db.add(room)

        amount, tier = (
            calculate_property_subscription_amount(
                db,
                district_id=request_property.district_id,
                total_rooms=request_property.total_rooms,
            )
        )

        subscription = PropertySubscription(
            landlord_id=landlord.id,
            property_id=property_record.id,
            total_rooms=request_property.total_rooms,
            monthly_amount=amount,
            pricing_tier=tier,
            status=SubscriptionStatus.active,
            start_date=date.today(),
            renewal_date=date.today() + timedelta(days=30),
        )

        db.add(subscription)

    request.status = LandlordRequestStatus.approved
    request.admin_note = payload.admin_note
    request.landlord_id = landlord.id
    request.approved_by_user_id = admin.id
    request.approved_at = datetime.now(timezone.utc)

    log_action(
        db,
        AuditAction.approve_landlord,
        admin,
        landlord.id,
        "LandlordRequest",
        request.id,
    )

    db.commit()

    db.refresh(request)
    db.refresh(landlord)

    return LandlordOnboardingResult(
        request=request,
        landlord=landlord,
        temporary_password=(
            password if not payload.password else None
        ),
    )


@router.post(
    "/manual",
    response_model=LandlordOnboardingResult,
)
def manually_create_landlord(
    payload: LandlordManualCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    landlord = create_landlord_account(
        db,
        full_name=payload.full_name,
        email=str(payload.email),
        phone=payload.phone,
        address=payload.address,
        password=payload.password,
    )

    db.commit()
    db.refresh(landlord)

    return LandlordOnboardingResult(
        request=None,
        landlord=landlord,
        temporary_password=None,
    )


@router.post(
    "",
    response_model=LandlordRead,
)
def create_landlord(
    payload: LandlordCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    landlord = Landlord(
        **payload.model_dump(),
        system_landlord_number=generate_landlord_number(db),
        is_active=True,
    )

    db.add(landlord)

    db.commit()
    db.refresh(landlord)

    return landlord


@router.get(
    "",
    response_model=list[LandlordRead],
)
def list_landlords(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.national_admin,
            UserRole.district_admin,
            UserRole.landlord,
        )
    ),
):
    ensure_landlord_numbers(db)

    if is_national_admin(current_user):
        return (
            db.query(Landlord)
            .order_by(Landlord.created_at.desc())
            .all()
        )

    if is_district_admin(current_user):
        district_ids = (
            get_district_admin_district_ids(
                db,
                current_user,
            )
        )

        if not district_ids:
            return []

        return (
            db.query(Landlord)
            .join(
                Property,
                Property.landlord_id == Landlord.id,
            )
            .filter(
                Property.district_id.in_(district_ids)
            )
            .distinct()
            .order_by(Landlord.created_at.desc())
            .all()
        )

    landlord = (
        db.query(Landlord)
        .filter(Landlord.user_id == current_user.id)
        .first()
    )

    return [landlord] if landlord else []


@router.post(
    "/{landlord_id}/disable",
    response_model=LandlordRead,
)
def disable_landlord(
    landlord_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    landlord = db.get(Landlord, landlord_id)

    if not landlord:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landlord not found",
        )

    landlord.is_active = False

    if landlord.user:
        landlord.user.is_active = False

    db.commit()
    db.refresh(landlord)

    return landlord


@router.delete(
    "/{landlord_id}",
    response_model=LandlordRead,
)
def delete_landlord(
    landlord_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    landlord = db.get(Landlord, landlord_id)

    if not landlord:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landlord not found",
        )

    landlord.is_active = False

    if landlord.user:
        landlord.user.is_active = False

    db.commit()
    db.refresh(landlord)

    return landlord
