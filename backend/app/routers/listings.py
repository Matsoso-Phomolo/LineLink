import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit import log_action
from app.application_rules import validate_application_record_against_listing
from app.auth import get_password_hash
from app.database import get_db
from app.dependencies import require_roles
from app.file_storage import save_upload_file
from app.identity import first_name_password, next_identifier
from app.lease_logic import generate_lease_for_occupancy
from app.models import (
    ApplicationStatus,
    AuditAction,
    District,
    DistrictArea,
    Landlord,
    ListingPhoto,
    ListingStatus,
    ListingVerificationStatus,
    Notification,
    Occupancy,
    OnboardingChecklist,
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
from app.notification_channels import send_login_credentials
from app.ownership import get_property_in_scope, get_room_in_scope, scoped_query
from app.rent_logic import generate_initial_rent_due
from app.room_status import is_vacant_room_status
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


def listing_scope_sql(user: User) -> tuple[str, dict[str, object]]:
    if user.role == UserRole.national_admin:
        return "", {}

    if user.role == UserRole.landlord and user.landlord_profile:
        return "where rl.landlord_id = :landlord_id", {
            "landlord_id": user.landlord_profile.id,
        }

    if user.role == UserRole.caretaker and user.caretaker_profile:
        return "where rl.landlord_id = :landlord_id", {
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
                where p.id = rl.property_id
                and daa.user_id = :user_id
                and daa.is_active is true
            )
            """,
            {"user_id": user.id},
        )

    return "where false", {}


def normalize_listing_status(raw_status: object) -> str:
    value = str(raw_status or "").strip().lower()
    return value if value in {item.value for item in ListingStatus} else ListingStatus.draft.value


def normalize_listing_verification_status(raw_status: object) -> str:
    value = str(raw_status or "").strip().lower()
    return (
        value
        if value in {item.value for item in ListingVerificationStatus}
        else ListingVerificationStatus.unverified.value
    )


def normalize_allowed_tenant_type(raw_type: object) -> str:
    value = str(raw_type or "").strip().lower()
    return value if value in {"student", "non_student", "both"} else "both"


def active_listing_query(db: Session, room_id: uuid.UUID):
    return db.query(RoomListing).filter(
        RoomListing.room_id == room_id,
        RoomListing.status.in_(
            [
                ListingStatus.draft,
                ListingStatus.published,
            ]
        ),
    )


def normalize_listing_room_type(raw_type: object) -> str:
    value = str(raw_type or "").strip().lower()
    return value if value in {"single", "double", "multiple"} else "single"


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


def listing_in_scope(
    db: Session,
    user: User,
    listing_id: uuid.UUID,
) -> RoomListing:
    listing = (
        scoped_query(db, user, RoomListing)
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
        require_roles(UserRole.national_admin, UserRole.landlord, UserRole.caretaker)
    ),
):
    prop = get_property_in_scope(db, user, payload.property_id)
    room = get_room_in_scope(db, user, payload.room_id)

    if room.property_id != prop.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room does not belong to the selected property",
        )

    payload_values = payload.model_dump()
    payload_values["district_id"] = payload.district_id or prop.district_id
    payload_values["area_id"] = payload.area_id or prop.area_id

    validate_district_area(db, payload_values["district_id"], payload_values["area_id"])

    if prop.district_id and payload_values["district_id"] != prop.district_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Listing district must match property district.",
        )

    if prop.area_id and payload_values["area_id"] != prop.area_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Listing area must match property area.",
        )

    if not is_vacant_room_status(room.status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only vacant rooms can be published as public listings.",
        )

    listing = (
        active_listing_query(db, room.id)
        .order_by(RoomListing.created_at.desc())
        .first()
    )

    if listing:
        for key, value in payload_values.items():
            setattr(listing, key, value)

        listing.landlord_id = prop.landlord_id
    else:
        listing = RoomListing(
            **payload_values,
            landlord_id=prop.landlord_id,
        )
        db.add(listing)

    if not listing.district_id:
        listing.district_id = prop.district_id

    if not listing.area_id:
        listing.area_id = prop.area_id

    if listing.is_public and listing.status == ListingStatus.published:
        listing.verification_status = ListingVerificationStatus.verified
        listing.is_verified = True

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
        require_roles(UserRole.national_admin, UserRole.landlord, UserRole.caretaker)
    ),
):
    where_sql, params = listing_scope_sql(user)
    rows = (
        db.execute(
            text(
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
                left join rooms r on r.id = rl.room_id
                left join properties p on p.id = rl.property_id
                {where_sql}
                order by rl.created_at desc
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
            "room_type": normalize_listing_room_type(row.get("room_type")),
            "allowed_tenant_type": normalize_allowed_tenant_type(
                row.get("allowed_tenant_type")
            ),
            "status": normalize_listing_status(row.get("status")),
            "verification_status": normalize_listing_verification_status(
                row.get("verification_status")
            ),
        }
        for row in rows
    ]


@router.put("/{listing_id}", response_model=ListingRead)
def update_listing(
    listing_id: uuid.UUID,
    payload: ListingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.national_admin, UserRole.landlord, UserRole.caretaker)
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

    validate_district_area(db, next_district_id, next_area_id)

    if prop.district_id and next_district_id != prop.district_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Listing district must match property district.",
        )

    if prop.area_id and next_area_id != prop.area_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Listing area must match property area.",
        )

    if values.get("status") == ListingStatus.published or values.get("is_public") is True:
        if not is_vacant_room_status(room.status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only vacant rooms can be published as public listings.",
            )
        duplicate = (
            active_listing_query(db, room.id)
            .filter(RoomListing.id != listing.id)
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This room already has an active listing.",
            )

    for key, value in values.items():
        setattr(listing, key, value)

    if not listing.district_id:
        listing.district_id = prop.district_id

    if not listing.area_id:
        listing.area_id = prop.area_id

    if listing.is_public and listing.status == ListingStatus.published:
        listing.verification_status = ListingVerificationStatus.verified
        listing.is_verified = True

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
        require_roles(UserRole.national_admin, UserRole.landlord, UserRole.caretaker)
    ),
):
    listing = listing_in_scope(db, user, listing_id)

    listing.status = ListingStatus.archived
    listing.is_public = False

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


@router.put("/{listing_id}/verify", response_model=ListingRead)
def verify_listing(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin)),
):
    listing = listing_in_scope(db, user, listing_id)

    listing.is_verified = True
    listing.verification_status = ListingVerificationStatus.verified

    room = db.get(Room, listing.room_id)

    if room and is_vacant_room_status(room.status):
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


@router.put("/{listing_id}/reject-verification", response_model=ListingRead)
def reject_listing_verification(
    listing_id: uuid.UUID,
    payload: ApplicationDecision,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin)),
):
    listing = listing_in_scope(db, user, listing_id)

    listing.is_verified = False
    listing.verification_status = ListingVerificationStatus.rejected
    listing.verification_note = payload.landlord_note
    listing.is_public = False

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


@router.post("/{listing_id}/photos", response_model=ListingPhotoRead)
def add_listing_photo(
    listing_id: uuid.UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.national_admin, UserRole.landlord, UserRole.caretaker)
    ),
):
    listing = listing_in_scope(db, user, listing_id)
    path = save_upload_file(file, "listing_photos")

    photo = ListingPhoto(listing_id=listing.id, file_path=path)

    db.add(photo)
    db.commit()
    db.refresh(photo)

    return photo


@router.get("/{listing_id}/viewing-requests", response_model=list[ViewingRequestRead])
def listing_viewing_requests(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.national_admin, UserRole.landlord, UserRole.caretaker)
    ),
):
    listing = listing_in_scope(db, user, listing_id)

    return (
        db.query(ViewingRequest)
        .filter(ViewingRequest.listing_id == listing.id)
        .order_by(ViewingRequest.created_at.desc())
        .all()
    )


@router.get("/{listing_id}/applications", response_model=list[TenantApplicationRead])
def listing_applications(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.national_admin, UserRole.landlord, UserRole.caretaker)
    ),
):
    listing = listing_in_scope(db, user, listing_id)

    return (
        db.query(TenantApplication)
        .filter(TenantApplication.listing_id == listing.id)
        .filter(TenantApplication.deleted_at.is_(None))
        .filter(
            (TenantApplication.status != ApplicationStatus.rejected)
            | (TenantApplication.rejection_expires_at.is_(None))
            | (TenantApplication.rejection_expires_at > datetime.now(timezone.utc))
        )
        .order_by(TenantApplication.created_at.desc())
        .all()
    )


@router.put("/applications/{application_id}/approve", response_model=TenantApplicationRead)
def approve_application(
    application_id: uuid.UUID,
    payload: ApplicationDecision,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.national_admin, UserRole.landlord, UserRole.caretaker)
    ),
):
    application = db.get(TenantApplication, application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    listing_in_scope(db, user, application.listing_id)

    application.status = ApplicationStatus.approved
    application.landlord_note = payload.landlord_note

    db.commit()
    db.refresh(application)

    return application


@router.put("/applications/{application_id}/reject", response_model=TenantApplicationRead)
def reject_application(
    application_id: uuid.UUID,
    payload: ApplicationDecision,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.national_admin, UserRole.landlord, UserRole.caretaker)
    ),
):
    application = db.get(TenantApplication, application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    listing_in_scope(db, user, application.listing_id)

    application.status = ApplicationStatus.rejected
    application.landlord_note = payload.landlord_note
    application.rejected_at = datetime.now(timezone.utc)
    application.rejection_expires_at = application.rejected_at + timedelta(minutes=60)

    db.commit()
    db.refresh(application)

    return application


@router.post("/applications/{application_id}/request-info", response_model=TenantApplicationRead)
def request_application_info(
    application_id: uuid.UUID,
    payload: ApplicationDecision,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.national_admin, UserRole.landlord, UserRole.caretaker)
    ),
):
    application = db.get(TenantApplication, application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    listing_in_scope(db, user, application.listing_id)

    application.status = ApplicationStatus.info_requested
    application.landlord_note = payload.landlord_note

    db.commit()
    db.refresh(application)

    return application


@router.post("/applications/{application_id}/assign-room")
def assign_application_room(
    application_id: uuid.UUID,
    payload: ApplicationAssignRoom,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.national_admin, UserRole.landlord, UserRole.caretaker)
    ),
):
    application = db.get(TenantApplication, application_id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    listing = listing_in_scope(db, user, application.listing_id)
    room = get_room_in_scope(db, user, listing.room_id)

    if listing.property_id != room.property_id or listing.landlord_id != room.landlord_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Listing, property, and room linkage is inconsistent",
        )

    if (
        not is_vacant_room_status(room.status)
        or listing.status != ListingStatus.published
        or not listing.is_public
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room is no longer available.",
        )

    validate_application_record_against_listing(
        listing,
        application.tenant_type,
        application.institution,
        application.student_number,
        application.occupation,
        application.tenant_category,
        application.tenant_subtype,
        application.institution_name,
        application.employer_or_business_name,
        application.work_location,
        application.number_of_occupants,
    )

    tenant = None

    if application.applicant_user_id:
        tenant = (
            db.query(Tenant)
            .filter(Tenant.user_id == application.applicant_user_id)
            .first()
        )

        if tenant and tenant.landlord_id != listing.landlord_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Applicant tenant profile belongs to another landlord",
            )

    tenant_user = None
    temporary_password = None

    if not tenant:
        if not application.applicant_user_id:
            temporary_password = first_name_password(application.full_name)

            tenant_user = User(
                username=next_identifier(db, UserRole.tenant),
                email=application.email or f"{uuid.uuid4()}@tenant.rentalink.local",
                phone=application.phone,
                full_name=application.full_name,
                role=UserRole.tenant,
                hashed_password=get_password_hash(temporary_password),
                must_change_password=True,
            )

            db.add(tenant_user)
            db.flush()

            application.applicant_user_id = tenant_user.id

        tenant = Tenant(
            user_id=application.applicant_user_id,
            landlord_id=listing.landlord_id,
            tenant_type=application.tenant_type,
            tenant_category=application.tenant_category,
            tenant_subtype=application.tenant_subtype,
            full_name=application.full_name,
            phone=application.phone,
            email=application.email,
            national_id=application.national_id,
            passport_number=application.passport_number,
            student_number=application.student_number,
            institution=application.institution,
            institution_name=application.institution_name,
            sponsor_or_guardian_name=application.sponsor_or_guardian_name,
            occupation=application.occupation,
            employer_or_business_name=application.employer_or_business_name,
            work_location=application.work_location,
            number_of_occupants=application.number_of_occupants,
            children_count=application.children_count,
            parking_required=application.parking_required,
            funding_source=application.funding_source,
            guarantor_name=application.guarantor_name,
            additional_notes=application.additional_notes,
            next_of_kin_name=application.emergency_contact_name
            or application.emergency_contact,
            next_of_kin_phone=application.emergency_contact_phone,
            lease_start_date=payload.move_in_date,
            monthly_rent=payload.monthly_rent,
            deposit_amount=payload.deposit_amount,
            outstanding_balance=payload.monthly_rent,
        )

        db.add(tenant)
        db.flush()

        if tenant_user and temporary_password:
            send_login_credentials(tenant_user, temporary_password)

    tenant.lease_start_date = payload.move_in_date
    tenant.monthly_rent = payload.monthly_rent
    tenant.deposit_amount = payload.deposit_amount

    checklist = (
        db.query(OnboardingChecklist)
        .filter(OnboardingChecklist.tenant_id == tenant.id)
        .first()
    )

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
    lease = generate_lease_for_occupancy(db, occupancy)

    room.status = RoomStatus.occupied
    listing.status = ListingStatus.rented
    listing.is_public = False

    application.room_id = listing.room_id
    application.property_id = listing.property_id
    application.landlord_id = listing.landlord_id
    application.status = ApplicationStatus.approved

    invitation = None

    if payload.create_invitation_if_no_user and not application.applicant_user_id:
        invitation = TenantInvitation(
            landlord_id=listing.landlord_id,
            tenant_application_id=application.id,
            tenant_id=tenant.id,
            email=application.email,
            phone=application.phone,
            token=str(uuid.uuid4()),
        )

        db.add(invitation)

    landlord = db.get(Landlord, listing.landlord_id)

    if landlord:
        db.add(
            Notification(
                user_id=landlord.user_id,
                title="Room assigned",
                body=f"{application.full_name} has been assigned to {room.room_number}.",
                category="applications",
            )
        )

    log_action(
        db,
        AuditAction.create_occupancy,
        user,
        listing.landlord_id,
        "TenantApplication",
        application.id,
    )

    db.commit()

    tenant_user = db.get(User, tenant.user_id) if tenant.user_id else None

    return {
        "tenant_id": tenant.id,
        "occupancy_id": occupancy.id,
        "lease_id": lease.id,
        "invitation_id": invitation.id if invitation else None,
        "username": tenant_user.username if tenant_user else None,
    }
