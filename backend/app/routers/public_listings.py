import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application_rules import validate_application_against_listing
from app.database import get_db
from app.models import (
    ApplicationStatus,
    DistrictArea,
    Landlord,
    ListingStatus,
    ListingVerificationStatus,
    Notification,
    PreferredResponseMethod,
    Room,
    RoomListing,
    RoomStatus,
    TenantApplication,
    TenantType,
    ViewingRequest,
)
from app.room_status import VACANT_ROOM_STATUSES
from app.schemas import (
    ListingRead,
    PublicApplicationSubmit,
    PublicRequestResponse,
    RoomInquiryCreate,
    TenantApplicationCreate,
    TenantApplicationRead,
    ViewingRequestCreate,
    ViewingRequestRead,
)

router = APIRouter(prefix="/public/listings", tags=["public listings"])
form_router = APIRouter(prefix="/public/applications", tags=["public applications"])


ROOM_UNAVAILABLE_MESSAGE = "Room is no longer available."


def get_public_listing(db: Session, listing_id: uuid.UUID) -> RoomListing:
    listing = (
        db.query(RoomListing)
        .join(Room, Room.id == RoomListing.room_id)
        .filter(
            RoomListing.id == listing_id,
            RoomListing.status == ListingStatus.published,
            RoomListing.is_public.is_(True),
            Room.status.in_(VACANT_ROOM_STATUSES),
        )
        .first()
    )

    if not listing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ROOM_UNAVAILABLE_MESSAGE,
        )

    return listing


@router.get("", response_model=list[ListingRead])
def public_listings(
    district_id: uuid.UUID | None = None,
    area_id: uuid.UUID | None = None,
    location_area: str | None = None,
    room_type: str | None = None,
    room_size: str | None = None,
    min_rent: float | None = None,
    max_rent: float | None = None,
    distance_from_nul: str | None = None,
    water_available: bool | None = None,
    electricity_available: bool | None = None,
    furnished: bool | None = None,
    verified_only: bool = False,
    db: Session = Depends(get_db),
):
    clauses = [
        "rl.status::text = :published_status",
        "rl.is_public is true",
        "r.status::text in ('vacant', 'available')",
    ]
    params: dict[str, object] = {
        "published_status": ListingStatus.published.value,
    }

    if verified_only:
        params["verified_status"] = ListingVerificationStatus.verified.value
        clauses.append("rl.verification_status::text = :verified_status")

    if district_id:
        clauses.append("rl.district_id = :district_id")
        params["district_id"] = district_id

    if area_id:
        clauses.append("rl.area_id = :area_id")
        params["area_id"] = area_id
    elif location_area:
        clauses.append(
            """
            (
                rl.location_area ilike :location_area
                or exists (
                    select 1
                    from district_areas da
                    where da.id = rl.area_id
                    and da.name ilike :location_area
                )
            )
            """
        )
        params["location_area"] = f"%{location_area}%"

    if room_type:
        clauses.append("rl.room_type::text = :room_type")
        params["room_type"] = room_type

    if room_size:
        clauses.append("rl.room_size ilike :room_size")
        params["room_size"] = f"%{room_size}%"

    if min_rent is not None:
        clauses.append("rl.rent_price >= :min_rent")
        params["min_rent"] = min_rent

    if max_rent is not None:
        clauses.append("rl.rent_price <= :max_rent")
        params["max_rent"] = max_rent

    if distance_from_nul:
        clauses.append("rl.distance_from_nul ilike :distance_from_nul")
        params["distance_from_nul"] = f"%{distance_from_nul}%"

    if water_available is not None:
        clauses.append("rl.water_available = :water_available")
        params["water_available"] = water_available

    if electricity_available is not None:
        clauses.append("rl.electricity_available = :electricity_available")
        params["electricity_available"] = electricity_available

    if furnished is not None:
        clauses.append("rl.furnished = :furnished")
        params["furnished"] = furnished

    sql = text(
        f"""
        select
            rl.id,
            rl.landlord_id,
            rl.property_id,
            rl.room_id,
            rl.district_id,
            rl.area_id,
            rl.title,
            rl.description,
            rl.rent_price,
            rl.deposit_amount,
            rl.room_type::text as room_type,
            rl.room_size,
            rl.location_area,
            rl.allowed_tenant_type::text as allowed_tenant_type,
            rl.available_from,
            rl.distance_from_nul,
            rl.contact_phone,
            rl.water_available,
            rl.electricity_available,
            rl.internet_included,
            rl.furnished,
            rl.parking_available,
            rl.pets_allowed,
            rl.gender_preference,
            rl.security_features,
            rl.house_rules,
            rl.status::text as status,
            rl.is_public,
            rl.is_verified,
            rl.verification_status::text as verification_status,
            rl.verification_note,
            r.room_number as room_number,
            p.name as property_name,
            rl.created_at
        from room_listings rl
        join rooms r on r.id = rl.room_id
        left join properties p on p.id = rl.property_id
        where {" and ".join(clauses)}
        order by
            case
                when rl.verification_status::text = :verified_status then 0
                else 1
            end,
            rl.created_at desc
        """
    )

    try:
        return [dict(row) for row in db.execute(sql, params).mappings().all()]
    except Exception:
        # Public search should degrade to an empty marketplace instead of
        # taking down the Room Finder if old production enum data is malformed.
        return []


@router.get("/{listing_id}", response_model=ListingRead)
def public_listing_detail(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return get_public_listing(db, listing_id)


@router.post(
    "/{listing_id}/viewing-requests",
    response_model=ViewingRequestRead,
)
def create_viewing_request(
    listing_id: uuid.UUID,
    payload: ViewingRequestCreate,
    db: Session = Depends(get_db),
):
    listing = get_public_listing(db, listing_id)

    request = ViewingRequest(
        listing_id=listing.id,
        **payload.model_dump(),
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    return request


@router.post(
    "/{listing_id}/applications",
    response_model=TenantApplicationRead,
)
def create_application(
    listing_id: uuid.UUID,
    payload: TenantApplicationCreate,
    db: Session = Depends(get_db),
):
    listing = get_public_listing(db, listing_id)
    validate_application_against_listing(listing, payload)

    application = TenantApplication(
        listing_id=listing.id,
        room_id=listing.room_id,
        property_id=listing.property_id,
        landlord_id=listing.landlord_id,
        status=ApplicationStatus.submitted,
        submitted_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )

    db.add(application)

    landlord = db.get(Landlord, listing.landlord_id)

    if landlord:
        db.add(
            Notification(
                user_id=landlord.user_id,
                title="New room request",
                body=f"{payload.full_name} is interested in {listing.title}.",
                category="applications",
            )
        )

    db.commit()
    db.refresh(application)

    return application


GENERIC_REQUEST_SUCCESS = (
    "Your request has been submitted. "
    "The landlord/caretaker will respond "
    "using your selected contact method."
)


def validate_response_method(payload: RoomInquiryCreate) -> None:
    if (
        payload.preferred_response_method
        == PreferredResponseMethod.email
        and not payload.email
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email is required for email responses.",
        )

    if (
        payload.preferred_response_method
        in {
            PreferredResponseMethod.phone_call,
            PreferredResponseMethod.whatsapp,
            PreferredResponseMethod.sms,
        }
        and not payload.phone
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number is required for the selected response method.",
        )


@router.post(
    "/{listing_id}/requests",
    response_model=PublicRequestResponse,
)
def create_room_request(
    listing_id: uuid.UUID,
    payload: RoomInquiryCreate,
    db: Session = Depends(get_db),
):
    listing = get_public_listing(db, listing_id)

    validate_response_method(payload)

    application = TenantApplication(
        listing_id=listing.id,
        room_id=listing.room_id,
        property_id=listing.property_id,
        landlord_id=listing.landlord_id,
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        tenant_type=TenantType.non_student,
        tenant_category="other",
        tenant_subtype="other",
        message=payload.message,
        preferred_response_method=payload.preferred_response_method,
        response_contact_value=(
            payload.email
            if payload.preferred_response_method
            == PreferredResponseMethod.email
            else payload.phone
        ),
        status=ApplicationStatus.inquiry_pending,
    )

    db.add(application)

    landlord = db.get(Landlord, listing.landlord_id)

    if landlord:
        db.add(
            Notification(
                user_id=landlord.user_id,
                title="New room request",
                body=f"{payload.full_name} is interested in {listing.title}.",
                category="applications",
            )
        )

    db.commit()

    return PublicRequestResponse(
        message=GENERIC_REQUEST_SUCCESS
    )


def get_application_by_token(
    db: Session,
    token: str,
) -> TenantApplication:
    application = (
        db.query(TenantApplication)
        .filter(TenantApplication.application_token == token)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application form link not found",
        )

    now = datetime.now(timezone.utc)

    expires_at = application.token_expires_at

    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at and expires_at < now:
        application.status = ApplicationStatus.expired
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Application form link has expired",
        )

    return application


@form_router.get(
    "/{token}",
    response_model=TenantApplicationRead,
)
def get_public_application_form(
    token: str,
    db: Session = Depends(get_db),
):
    return get_application_by_token(db, token)


@form_router.post(
    "/{token}",
    response_model=TenantApplicationRead,
)
def submit_public_application_form(
    token: str,
    payload: PublicApplicationSubmit,
    db: Session = Depends(get_db),
):
    application = get_application_by_token(db, token)

    listing = get_public_listing(db, application.listing_id)
    validate_application_against_listing(listing, payload)

    for key, value in payload.model_dump().items():
        setattr(application, key, value)

    application.room_id = listing.room_id
    application.property_id = listing.property_id
    application.landlord_id = listing.landlord_id
    application.status = ApplicationStatus.submitted
    application.submitted_at = datetime.now(timezone.utc)

    landlord = db.get(Landlord, application.landlord_id)

    if landlord:
        db.add(
            Notification(
                user_id=landlord.user_id,
                title="Application form submitted",
                body=(
                    f"{application.full_name} submitted "
                    f"full details for review."
                ),
                category="applications",
            )
        )

    db.commit()
    db.refresh(application)

    return application
