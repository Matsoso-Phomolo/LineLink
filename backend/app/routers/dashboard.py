from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dashboard_logic import (
    calculate_collection_rate,
    calculate_landlord_revenue,
    calculate_occupancy_rate,
    calculate_overdue_exposure,
    calculate_property_financial_summary,
)
from app.database import get_db
from app.dependencies import (
    get_district_admin_district_ids,
    is_district_admin,
    is_national_admin,
    require_roles,
)
from app.models import (
    ApplicationStatus,
    Landlord,
    LandlordRequest,
    LandlordRequestStatus,
    ListingStatus,
    Occupancy,
    OccupancyStatus,
    PaymentSubmission,
    PaymentSubmissionStatus,
    Property,
    RentDue,
    RentDueStatus,
    Room,
    RoomListing,
    RoomStatus,
    SupportTicket,
    Tenant,
    TenantApplication,
    TicketStatus,
    User,
    UserRole,
)
from app.ownership import scoped_query
from app.schemas import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def scoped_applications_query(
    db: Session,
    user: User,
):
    scoped_listing_ids = [
        listing.id
        for listing in scoped_query(db, user, RoomListing).all()
    ]

    if not scoped_listing_ids:
        return db.query(TenantApplication).filter(False)

    return db.query(TenantApplication).filter(
        TenantApplication.listing_id.in_(scoped_listing_ids)
    )


def get_landlord_id_for_dashboard(user: User):
    if user.role == UserRole.landlord and user.landlord_profile:
        return user.landlord_profile.id

    if user.role == UserRole.caretaker and user.caretaker_profile:
        return user.caretaker_profile.landlord_id

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Financial dashboard is available only for landlord/caretaker scoped users.",
    )


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.national_admin,
            UserRole.district_admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    props = scoped_query(db, user, Property)
    rooms = scoped_query(db, user, Room)
    occupancies = scoped_query(db, user, Occupancy)
    rent_dues = scoped_query(db, user, RentDue)
    payment_submissions = scoped_query(db, user, PaymentSubmission)
    listings = scoped_query(db, user, RoomListing)
    support_tickets = scoped_query(db, user, SupportTicket)
    tenants = scoped_query(db, user, Tenant)
    scoped_applications = scoped_applications_query(db, user)

    active_landlords = 0
    pending_landlord_requests = 0

    if is_national_admin(user):
        active_landlords = (
            db.query(Landlord)
            .filter(Landlord.is_active.is_(True))
            .count()
        )

        pending_landlord_requests = (
            db.query(LandlordRequest)
            .filter(LandlordRequest.status == LandlordRequestStatus.pending)
            .count()
        )

    elif is_district_admin(user):
        district_ids = get_district_admin_district_ids(db, user)

        if district_ids:
            active_landlords = (
                db.query(Landlord)
                .join(Property, Property.landlord_id == Landlord.id)
                .filter(
                    Landlord.is_active.is_(True),
                    Property.district_id.in_(district_ids),
                )
                .distinct()
                .count()
            )

            pending_landlord_requests = (
                db.query(LandlordRequest)
                .join(Property, Property.landlord_id == LandlordRequest.landlord_id)
                .filter(
                    LandlordRequest.status == LandlordRequestStatus.pending,
                    Property.district_id.in_(district_ids),
                )
                .distinct()
                .count()
            )

    return DashboardSummary(
        properties=props.count(),
        rooms=rooms.count(),
        vacant_rooms=rooms.filter(Room.status == RoomStatus.vacant).count(),
        occupied_rooms=rooms.filter(
            Room.status.in_(
                [
                    RoomStatus.partially_occupied,
                    RoomStatus.full,
                ]
            )
        ).count(),
        active_tenants=occupancies.filter(
            Occupancy.status == OccupancyStatus.active
        ).count(),
        unpaid_rent_dues=rent_dues.filter(
            RentDue.status.in_(
                [
                    RentDueStatus.unpaid,
                    RentDueStatus.partial,
                    RentDueStatus.overdue,
                ]
            )
        ).count(),
        pending_payment_submissions=payment_submissions.filter(
            PaymentSubmission.status == PaymentSubmissionStatus.pending
        ).count(),
        published_listings=listings.filter(
            RoomListing.status == ListingStatus.published
        ).count(),
        pending_applications=scoped_applications.filter(
            TenantApplication.status.in_(
                [
                    ApplicationStatus.inquiry_pending,
                    ApplicationStatus.form_sent,
                    ApplicationStatus.submitted,
                    ApplicationStatus.pending,
                    ApplicationStatus.under_review,
                    ApplicationStatus.info_requested,
                ]
            )
        ).count(),
        pending_room_requests=scoped_applications.filter(
            TenantApplication.status == ApplicationStatus.inquiry_pending
        ).count(),
        maintenance_tickets=support_tickets.filter(
            SupportTicket.status.in_(
                [
                    TicketStatus.open,
                    TicketStatus.assigned,
                    TicketStatus.in_progress,
                ]
            )
        ).count(),
        overdue_rent_dues=rent_dues.filter(
            RentDue.status == RentDueStatus.overdue
        ).count(),
        active_landlords=active_landlords,
        pending_landlord_requests=pending_landlord_requests,
        total_tenants=tenants.count(),
    )


@router.get("/financial-summary")
def financial_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker)),
):
    landlord_id = get_landlord_id_for_dashboard(user)
    return calculate_property_financial_summary(db, landlord_id)


@router.get("/revenue")
def revenue_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker)),
):
    landlord_id = get_landlord_id_for_dashboard(user)
    return calculate_landlord_revenue(db, landlord_id)


@router.get("/occupancy")
def occupancy_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker)),
):
    landlord_id = get_landlord_id_for_dashboard(user)
    return calculate_occupancy_rate(db, landlord_id)


@router.get("/overdue")
def overdue_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker)),
):
    landlord_id = get_landlord_id_for_dashboard(user)
    return calculate_overdue_exposure(db, landlord_id)


@router.get("/collection-rate")
def collection_rate_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker)),
):
    landlord_id = get_landlord_id_for_dashboard(user)
    return calculate_collection_rate(db, landlord_id)
