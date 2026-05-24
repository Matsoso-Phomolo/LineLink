import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.audit import log_action
from app.database import get_db
from app.dependencies import require_roles
from app.file_storage import save_upload_file
from app.models import (
    ApplicationStatus,
    AuditAction,
    ListingPhoto,
    ListingStatus,
    Landlord,
    Notification,
    Occupancy,
    OnboardingChecklist,
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


def listing_in_scope(db: Session, user: User, listing_id: uuid.UUID) -> RoomListing:
    listing = landlord_scope_filter(db, user, RoomListing).filter(RoomListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing


@router.post("", response_model=ListingRead)
def create_listing(payload: ListingCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    prop = get_property_in_scope(db, user, payload.property_id)
    room = get_room_in_scope(db, user, payload.room_id)
    if room.property_id != prop.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room does not belong to the selected property")
    listing = RoomListing(**payload.model_dump(), landlord_id=prop.landlord_id)
    if room.status == RoomStatus.occupied:
        listing.status = ListingStatus.rented
        listing.is_public = False
    db.add(listing)
    log_action(db, AuditAction.create_room_listing, user, prop.landlord_id, "RoomListing")
    db.commit()
    db.refresh(listing)
    return listing


@router.get("/mine", response_model=list[ListingRead])
def my_listings(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    return landlord_scope_filter(db, user, RoomListing).order_by(RoomListing.created_at.desc()).all()


@router.put("/{listing_id}", response_model=ListingRead)
def update_listing(listing_id: uuid.UUID, payload: ListingUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    listing = listing_in_scope(db, user, listing_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(listing, key, value)
    log_action(db, AuditAction.update_room_listing, user, listing.landlord_id, "RoomListing", listing.id)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/{listing_id}", response_model=ListingRead)
def archive_listing(listing_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    listing = listing_in_scope(db, user, listing_id)
    listing.status = ListingStatus.archived
    listing.is_public = False
    db.commit()
    db.refresh(listing)
    return listing


@router.post("/{listing_id}/photos", response_model=ListingPhotoRead)
def add_listing_photo(listing_id: uuid.UUID, file: UploadFile, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    listing = listing_in_scope(db, user, listing_id)
    path = save_upload_file(file, "listing_photos")
    photo = ListingPhoto(listing_id=listing.id, file_path=path)
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.get("/{listing_id}/viewing-requests", response_model=list[ViewingRequestRead])
def listing_viewing_requests(listing_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    listing = listing_in_scope(db, user, listing_id)
    return db.query(ViewingRequest).filter(ViewingRequest.listing_id == listing.id).order_by(ViewingRequest.created_at.desc()).all()


@router.get("/{listing_id}/applications", response_model=list[TenantApplicationRead])
def listing_applications(listing_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    listing = listing_in_scope(db, user, listing_id)
    return db.query(TenantApplication).filter(TenantApplication.listing_id == listing.id).order_by(TenantApplication.created_at.desc()).all()


@router.put("/applications/{application_id}/approve", response_model=TenantApplicationRead)
def approve_application(application_id: uuid.UUID, payload: ApplicationDecision, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    application = db.get(TenantApplication, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    listing = listing_in_scope(db, user, application.listing_id)
    application.status = ApplicationStatus.approved
    application.landlord_note = payload.landlord_note
    db.commit()
    db.refresh(application)
    return application


@router.put("/applications/{application_id}/reject", response_model=TenantApplicationRead)
def reject_application(application_id: uuid.UUID, payload: ApplicationDecision, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    application = db.get(TenantApplication, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    listing_in_scope(db, user, application.listing_id)
    application.status = ApplicationStatus.rejected
    application.landlord_note = payload.landlord_note
    db.commit()
    db.refresh(application)
    return application


@router.post("/applications/{application_id}/request-info", response_model=TenantApplicationRead)
def request_application_info(application_id: uuid.UUID, payload: ApplicationDecision, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    application = db.get(TenantApplication, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    listing_in_scope(db, user, application.listing_id)
    application.status = ApplicationStatus.info_requested
    application.landlord_note = payload.landlord_note
    db.commit()
    db.refresh(application)
    return application


@router.post("/applications/{application_id}/assign-room")
def assign_application_room(application_id: uuid.UUID, payload: ApplicationAssignRoom, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    application = db.get(TenantApplication, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    listing = listing_in_scope(db, user, application.listing_id)
    room = get_room_in_scope(db, user, listing.room_id)
    if listing.property_id != room.property_id or listing.landlord_id != room.landlord_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Listing, property, and room linkage is inconsistent")
    if room.status != RoomStatus.vacant or listing.status != ListingStatus.published or not listing.is_public:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is no longer available.")
    tenant = None
    if application.applicant_user_id:
        tenant = db.query(Tenant).filter(Tenant.user_id == application.applicant_user_id).first()
        if tenant and tenant.landlord_id != listing.landlord_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Applicant tenant profile belongs to another landlord")
    if not tenant:
        tenant = Tenant(
            user_id=application.applicant_user_id,
            landlord_id=listing.landlord_id,
            tenant_type=application.tenant_type,
            full_name=application.full_name,
            phone=application.phone,
            email=application.email,
            national_id=application.national_id,
            passport_number=application.passport_number,
            student_number=application.student_number,
            institution=application.institution,
            occupation=application.occupation,
            next_of_kin_name=application.emergency_contact_name or application.emergency_contact,
            next_of_kin_phone=application.emergency_contact_phone,
            lease_start_date=payload.move_in_date,
            monthly_rent=payload.monthly_rent,
            deposit_amount=payload.deposit_amount,
            outstanding_balance=payload.monthly_rent,
        )
        db.add(tenant)
        db.flush()
    tenant.lease_start_date = payload.move_in_date
    tenant.monthly_rent = payload.monthly_rent
    tenant.deposit_amount = payload.deposit_amount
    checklist = db.query(OnboardingChecklist).filter(OnboardingChecklist.tenant_id == tenant.id).first()
    if not checklist:
        checklist = OnboardingChecklist(tenant_id=tenant.id)
        db.add(checklist)
    checklist.documents_submitted = bool(application.document_path)
    checklist.room_assigned = True
    checklist.occupancy_activated = True
    occupancy = Occupancy(
        landlord_id=listing.landlord_id,
        tenant_id=tenant.id,
        room_id=room.id,
        move_in_date=payload.move_in_date,
        monthly_rent=payload.monthly_rent,
        deposit_amount=payload.deposit_amount,
        billing_start_month=payload.billing_start_month,
    )
    db.add(occupancy)
    db.flush()
    generate_initial_rent_due(db, occupancy)
    room.status = RoomStatus.occupied
    listing.status = ListingStatus.rented
    listing.is_public = False
    application.room_id = listing.room_id
    application.property_id = listing.property_id
    application.landlord_id = listing.landlord_id
    application.status = ApplicationStatus.approved
    invitation = None
    if payload.create_invitation_if_no_user and not application.applicant_user_id:
        invitation = TenantInvitation(landlord_id=listing.landlord_id, tenant_application_id=application.id, tenant_id=tenant.id, email=application.email, phone=application.phone, token=str(uuid.uuid4()))
        db.add(invitation)
    landlord = db.get(Landlord, listing.landlord_id)
    if landlord:
        db.add(Notification(user_id=landlord.user_id, title="Room assigned", body=f"{application.full_name} has been assigned to {room.room_number}.", category="applications"))
    log_action(db, AuditAction.create_occupancy, user, listing.landlord_id, "TenantApplication", application.id)
    db.commit()
    return {"tenant_id": tenant.id, "occupancy_id": occupancy.id, "invitation_id": invitation.id if invitation else None}
