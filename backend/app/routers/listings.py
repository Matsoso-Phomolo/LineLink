import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.audit import log_action
from app.database import get_db
from app.dependencies import require_roles
from app.file_storage import save_upload_file
from app.auth import get_password_hash
from app.identity import first_name_password, next_identifier
from app.notification_channels import send_login_credentials
from app.lease_logic import generate_lease_for_occupancy
from app.models import (
    ApplicationStatus,
    AuditAction,
    District,
    DistrictArea,
    ListingPhoto,
    ListingStatus,
    ListingVerificationStatus,
    Landlord,
    Notification,
    Occupancy,
    OnboardingChecklist,
    Property,
    Room,
    RoomListing,
    RoomStatus,
    Tenant,
    TenantApplication,
    TenantInvitation,
    User,
    UserRole,
    ViewingRequest,
)
from app.ownership import get_property_in_scope, get_room_in_scope, landlord_scope_filter
from app.rent_logic import generate_initial_rent_due
from app.schemas import (
    ApplicationAssignRoom,
    ApplicationDecision,
    ListingCreate,
    ListingPhotoRead,
    ListingRead,
    ListingUpdate,
    TenantApplicationRead,
    ViewingRequestRead,
)

router = APIRouter(prefix="/listings", tags=["listings"])


def validate_district_area(
    db: Session,
    district_id: uuid.UUID | None,
    area_id: uuid.UUID | None,
) -> None:
    if not district_id and not area_id:
        return

    if not district_id or not area_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both district_id and area_id are required together.",
        )

    district = db.get(District, district_id)

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found.",
        )

    area = db.get(DistrictArea, area_id)

    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found.",
        )

    if area.district_id != district.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected area does not belong to selected district.",
        )


def listing_in_scope(db: Session, user: User, listing_id: uuid.UUID) -> RoomListing:
    listing = (
        landlord_scope_filter(db, user, RoomListing)
        .filter(RoomListing.id == listing_id)
        .first()
    )

    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )

    return listing


@router.post("", response_model=ListingRead)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    prop = get_property_in_scope(db, user, payload.property_id)

    room = get_room_in_scope(db, user, payload.room_id)

    if room.property_id != prop.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room does not belong to the selected property",
        )

    validate_district_area(
        db=db,
        district_id=payload.district_id,
        area_id=payload.area_id,
    )

    if payload.district_id and prop.district_id:
        if payload.district_id != prop.district_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Listing district must match property district.",
            )

    if payload.area_id and prop.area_id:
        if payload.area_id != prop.area_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Listing area must match property area.",
            )

    existing_listing = (
        db.query(RoomListing)
        .filter(
            RoomListing.room_id == room.id,
            RoomListing.status != ListingStatus.rented,
        )
        .order_by(RoomListing.created_at.desc())
        .first()
    )

    if existing_listing:
        for key, value in payload.model_dump().items():
            setattr(existing_listing, key, value)

        existing_listing.landlord_id = prop.landlord_id

        listing = existing_listing

    else:
        listing = RoomListing(
            **payload.model_dump(),
            landlord_id=prop.landlord_id,
        )

        db.add(listing)

    if not listing.district_id:
        listing.district_id = prop.district_id

    if not listing.area_id:
        listing.area_id = prop.area_id

    if listing.is_public and listing.status == ListingStatus.published:
        listing.verification_status = ListingVerificationStatus.pending_verification
        listing.is_verified = False

    if room.status == RoomStatus.occupied:
        listing.status = ListingStatus.rented
        listing.is_public = False

    log_action(
        db,
        AuditAction.create_room_listing,
        user,
        prop.landlord_id,
        "RoomListing",
    )

    db.commit()
    db.refresh(listing)

    return listing


@router.get("/mine", response_model=list[ListingRead])
def my_listings(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    return (
        landlord_scope_filter(db, user, RoomListing)
        .order_by(RoomListing.created_at.desc())
        .all()
    )


@router.put("/{listing_id}", response_model=ListingRead)
def update_listing(
    listing_id: uuid.UUID,
    payload: ListingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    listing = listing_in_scope(db, user, listing_id)

    values = payload.model_dump(exclude_unset=True)

    property_id = values.get("property_id", listing.property_id)
    room_id = values.get("room_id", listing.room_id)

    prop = get_property_in_scope(db, user, property_id)

    room = get_room_in_scope(db, user, room_id)

    if room.property_id != prop.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room does not belong to the selected property",
        )

    next_district_id = values.get("district_id", listing.district_id)
    next_area_id = values.get("area_id", listing.area_id)

    validate_district_area(
        db=db,
        district_id=next_district_id,
        area_id=next_area_id,
    )

    if next_district_id and prop.district_id:
        if next_district_id != prop.district_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Listing district must match property district.",
            )

    if next_area_id and prop.area_id:
        if next_area_id != prop.area_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Listing area must match property area.",
            )

    for key, value in values.items():
        setattr(listing, key, value)

    if not listing.district_id:
        listing.district_id = prop.district_id

    if not listing.area_id:
        listing.area_id = prop.area_id

    if (
        listing.is_public
        and listing.status == ListingStatus.published
        and listing.verification_status != ListingVerificationStatus.verified
    ):
        listing.verification_status = (
            ListingVerificationStatus.pending_verification
        )

        listing.is_verified = False

    log_action(
        db,
        AuditAction.verify_listing,
        user,
        listing.landlord_id,
        "RoomListing",
        listing.id,
    )

    db.commit()
    db.refresh(listing)

    return listing


@router.delete("/{listing_id}", response_model=ListingRead)
def archive_listing(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    listing = listing_in_scope(db, user, listing_id)

    listing.status = ListingStatus.archived
    listing.is_public = False

    db.commit()
    db.refresh(listing)

    return listing


@router.put("/{listing_id}/verify", response_model=ListingRead)
def verify_listing(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin)),
):
    listing = db.get(RoomListing, listing_id)

    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )

    listing.is_verified = True
    listing.verification_status = ListingVerificationStatus.verified

    room = db.get(Room, listing.room_id)

    if room and room.status == RoomStatus.vacant:
        listing.status = ListingStatus.published
        listing.is_public = True

    log_action(
        db,
        AuditAction.update_room_listing,
        user,
        listing.landlord_id,
        "RoomListing",
        listing.id,
    )

    db.commit()
    db.refresh(listing)

    return listing
