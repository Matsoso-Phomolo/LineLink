import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ApplicationStatus, Landlord, ListingStatus, Notification, Room, RoomListing, RoomStatus, TenantApplication, TenantType, ViewingRequest
from app.schemas import (
    ListingRead,
    PublicApplicationSubmit,
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
    listing = db.query(RoomListing).join(Room, Room.id == RoomListing.room_id).filter(
        RoomListing.id == listing_id,
        RoomListing.status == ListingStatus.published,
        RoomListing.is_public.is_(True),
        RoomListing.is_verified.is_(True),
        Room.status == RoomStatus.vacant,
    ).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ROOM_UNAVAILABLE_MESSAGE)
    return listing


@router.get("", response_model=list[ListingRead])
def public_listings(location_area: str | None = None, room_type: str | None = None, max_rent: float | None = None, db: Session = Depends(get_db)):
    query = db.query(RoomListing).join(Room, Room.id == RoomListing.room_id).filter(
        RoomListing.status == ListingStatus.published,
        RoomListing.is_public.is_(True),
        RoomListing.is_verified.is_(True),
        Room.status == RoomStatus.vacant,
    )
    if location_area:
        query = query.filter(RoomListing.location_area.ilike(f"%{location_area}%"))
    if room_type:
        query = query.filter(RoomListing.room_type == room_type)
    if max_rent:
        query = query.filter(RoomListing.rent_price <= max_rent)
    return query.order_by(RoomListing.created_at.desc()).all()


@router.get("/{listing_id}", response_model=ListingRead)
def public_listing_detail(listing_id: uuid.UUID, db: Session = Depends(get_db)):
    return get_public_listing(db, listing_id)


@router.post("/{listing_id}/viewing-requests", response_model=ViewingRequestRead)
def create_viewing_request(listing_id: uuid.UUID, payload: ViewingRequestCreate, db: Session = Depends(get_db)):
    listing = get_public_listing(db, listing_id)
    request = ViewingRequest(listing_id=listing.id, **payload.model_dump())
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.post("/{listing_id}/applications", response_model=TenantApplicationRead)
def create_application(listing_id: uuid.UUID, payload: TenantApplicationCreate, db: Session = Depends(get_db)):
    listing = get_public_listing(db, listing_id)
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
        db.add(Notification(user_id=landlord.user_id, title="New room request", body=f"{payload.full_name} is interested in {listing.title}.", category="applications"))
    db.commit()
    db.refresh(application)
    return application


@router.post("/{listing_id}/requests", response_model=TenantApplicationRead)
def create_room_request(listing_id: uuid.UUID, payload: RoomInquiryCreate, db: Session = Depends(get_db)):
    listing = get_public_listing(db, listing_id)
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
        status=ApplicationStatus.inquiry_pending,
    )
    db.add(application)
    landlord = db.get(Landlord, listing.landlord_id)
    if landlord:
        db.add(Notification(user_id=landlord.user_id, title="New room request", body=f"{payload.full_name} is interested in {listing.title}.", category="applications"))
    db.commit()
    db.refresh(application)
    return application


def get_application_by_token(db: Session, token: str) -> TenantApplication:
    application = db.query(TenantApplication).filter(TenantApplication.application_token == token).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application form link not found")
    now = datetime.now(timezone.utc)
    expires_at = application.token_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < now:
        application.status = ApplicationStatus.expired
        db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Application form link has expired")
    return application


@form_router.get("/{token}", response_model=TenantApplicationRead)
def get_public_application_form(token: str, db: Session = Depends(get_db)):
    return get_application_by_token(db, token)


@form_router.post("/{token}", response_model=TenantApplicationRead)
def submit_public_application_form(token: str, payload: PublicApplicationSubmit, db: Session = Depends(get_db)):
    application = get_application_by_token(db, token)
    listing = get_public_listing(db, application.listing_id)
    for key, value in payload.model_dump().items():
        setattr(application, key, value)
    application.room_id = listing.room_id
    application.property_id = listing.property_id
    application.landlord_id = listing.landlord_id
    application.status = ApplicationStatus.submitted
    application.submitted_at = datetime.now(timezone.utc)
    landlord = db.get(Landlord, application.landlord_id)
    if landlord:
        db.add(Notification(user_id=landlord.user_id, title="Application form submitted", body=f"{application.full_name} submitted full details for review.", category="applications"))
    db.commit()
    db.refresh(application)
    return application
