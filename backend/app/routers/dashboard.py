from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
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
from app.room_status import VACANT_ROOM_STATUSES
from app.schemas import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def count_scalar(db: Session, sql: str, params: dict[str, object] | None = None) -> int:
    try:
        return int(db.execute(text(sql), params or {}).scalar() or 0)
    except Exception:
        return 0


def dashboard_scope(user: User, alias: str) -> tuple[str, dict[str, object]]:
    if user.role == UserRole.national_admin:
        return "", {}

    if user.role == UserRole.landlord and user.landlord_profile:
        return f"where {alias}.landlord_id = :landlord_id", {
            "landlord_id": user.landlord_profile.id,
        }

    if user.role == UserRole.caretaker and user.caretaker_profile:
        return f"where {alias}.landlord_id = :landlord_id", {
            "landlord_id": user.caretaker_profile.landlord_id,
        }

    if user.role == UserRole.district_admin:
        return (
            f"""
            where exists (
                select 1
                from properties p
                join district_admin_assignments daa
                    on daa.district_id = p.district_id
                where p.landlord_id = {alias}.landlord_id
                and daa.user_id = :user_id
                and daa.is_active is true
            )
            """,
            {"user_id": user.id},
        )

    return "where false", {}


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
    property_where, property_params = dashboard_scope(user, "properties")
    room_where, room_params = dashboard_scope(user, "rooms")
    occupancy_where, occupancy_params = dashboard_scope(user, "occupancies")
    rent_where, rent_params = dashboard_scope(user, "rent_dues")
    payment_where, payment_params = dashboard_scope(user, "payment_submissions")
    listing_where, listing_params = dashboard_scope(user, "room_listings")
    tenant_where, tenant_params = dashboard_scope(user, "tenants")

    active_landlords = count_scalar(
        db,
        "select count(*) from landlords where is_active is true",
    ) if is_national_admin(user) else 0
    pending_landlord_requests = count_scalar(
        db,
        "select count(*) from landlord_requests where status::text = 'pending'",
    ) if is_national_admin(user) else 0

    return DashboardSummary(
        properties=count_scalar(db, f"select count(*) from properties {property_where}", property_params),
        rooms=count_scalar(db, f"select count(*) from rooms {room_where}", room_params),
        vacant_rooms=count_scalar(
            db,
            f"select count(*) from rooms {room_where} {'and' if room_where else 'where'} status::text in ('vacant','available')",
            room_params,
        ),
        occupied_rooms=count_scalar(
            db,
            f"select count(*) from rooms {room_where} {'and' if room_where else 'where'} status::text in ('occupied','partially_occupied','full')",
            room_params,
        ),
        active_tenants=count_scalar(
            db,
            f"select count(*) from occupancies {occupancy_where} {'and' if occupancy_where else 'where'} status::text = 'active'",
            occupancy_params,
        ),
        unpaid_rent_dues=count_scalar(
            db,
            f"select count(*) from rent_dues {rent_where} {'and' if rent_where else 'where'} status::text in ('unpaid','partial','overdue')",
            rent_params,
        ),
        pending_payment_submissions=count_scalar(
            db,
            f"select count(*) from payment_submissions {payment_where} {'and' if payment_where else 'where'} status::text = 'pending'",
            payment_params,
        ),
        published_listings=count_scalar(
            db,
            f"select count(*) from room_listings {listing_where} {'and' if listing_where else 'where'} status::text = 'published'",
            listing_params,
        ),
        pending_applications=count_scalar(
            db,
            f"""
            select count(*)
            from tenant_applications ta
            join room_listings rl on rl.id = ta.listing_id
            {listing_where.replace('room_listings', 'rl')}
            {'and' if listing_where else 'where'} ta.status::text in ('inquiry_pending','form_sent','submitted','pending','under_review','info_requested')
            """,
            listing_params,
        ),
        pending_room_requests=count_scalar(
            db,
            f"""
            select count(*)
            from tenant_applications ta
            join room_listings rl on rl.id = ta.listing_id
            {listing_where.replace('room_listings', 'rl')}
            {'and' if listing_where else 'where'} ta.status::text = 'inquiry_pending'
            """,
            listing_params,
        ),
        maintenance_tickets=count_scalar(
            db,
            "select count(*) from support_tickets where status::text in ('open','assigned','in_progress')",
        ),
        overdue_rent_dues=count_scalar(
            db,
            f"select count(*) from rent_dues {rent_where} {'and' if rent_where else 'where'} status::text = 'overdue'",
            rent_params,
        ),
        active_landlords=active_landlords,
        pending_landlord_requests=pending_landlord_requests,
        total_tenants=count_scalar(db, f"select count(*) from tenants {tenant_where}", tenant_params),
    )

    property_where, property_params = dashboard_scope(user, "properties")
    room_where, room_params = dashboard_scope(user, "rooms")
    occupancy_where, occupancy_params = dashboard_scope(user, "occupancies")
    rent_where, rent_params = dashboard_scope(user, "rent_dues")
    payment_where, payment_params = dashboard_scope(user, "payment_submissions")
    listing_where, listing_params = dashboard_scope(user, "room_listings")
    tenant_where, tenant_params = dashboard_scope(user, "tenants")

    active_landlords = 0
    pending_landlord_requests = 0

    if is_national_admin(user):
        active_landlords = count_scalar(
            db,
            "select count(*) from landlords where is_active is true",
        )

        pending_landlord_requests = count_scalar(
            db,
            "select count(*) from landlord_requests where status::text = 'pending'",
        )

    elif is_district_admin(user):
        district_ids = get_district_admin_district_ids(db, user)

        if district_ids:
            active_landlords = count_scalar(
                db,
                """
                select count(distinct l.id)
                from landlords l
                join properties p on p.landlord_id = l.id
                where l.is_active is true
                and p.district_id = any(:district_ids)
                """,
                {"district_ids": district_ids},
            )

            pending_landlord_requests = count_scalar(
                db,
                """
                select count(distinct lr.id)
                from landlord_requests lr
                join properties p on p.landlord_id = lr.landlord_id
                where lr.status::text = 'pending'
                and p.district_id = any(:district_ids)
                """,
                {"district_ids": district_ids},
            )

    return DashboardSummary(
        properties=count_scalar(db, f"select count(*) from properties {property_where}", property_params),
        rooms=count_scalar(db, f"select count(*) from rooms {room_where}", room_params),
        vacant_rooms=count_scalar(
            db,
            f"select count(*) from rooms {room_where} {'and' if room_where else 'where'} status::text in ('vacant','available')",
            room_params,
        ),
        occupied_rooms=count_scalar(
            db,
            f"select count(*) from rooms {room_where} {'and' if room_where else 'where'} status::text in ('occupied','partially_occupied','full')",
            room_params,
        ),
        active_tenants=count_scalar(
            db,
            f"select count(*) from occupancies {occupancy_where} {'and' if occupancy_where else 'where'} status::text = 'active'",
            occupancy_params,
        ),
        unpaid_rent_dues=count_scalar(
            db,
            f"select count(*) from rent_dues {rent_where} {'and' if rent_where else 'where'} status::text in ('unpaid','partial','overdue')",
            rent_params,
        ),
        pending_payment_submissions=count_scalar(
            db,
            f"select count(*) from payment_submissions {payment_where} {'and' if payment_where else 'where'} status::text = 'pending'",
            payment_params,
        ),
        published_listings=count_scalar(
            db,
            f"select count(*) from room_listings {listing_where} {'and' if listing_where else 'where'} status::text = 'published'",
            listing_params,
        ),
        pending_applications=count_scalar(
            db,
            f"""
            select count(*)
            from tenant_applications ta
            join room_listings rl on rl.id = ta.listing_id
            {listing_where.replace('room_listings', 'rl')}
            {'and' if listing_where else 'where'} ta.status::text in ('inquiry_pending','form_sent','submitted','pending','under_review','info_requested')
            """,
            listing_params,
        ),
        pending_room_requests=count_scalar(
            db,
            f"""
            select count(*)
            from tenant_applications ta
            join room_listings rl on rl.id = ta.listing_id
            {listing_where.replace('room_listings', 'rl')}
            {'and' if listing_where else 'where'} ta.status::text = 'inquiry_pending'
            """,
            listing_params,
        ),
        maintenance_tickets=count_scalar(
            db,
            "select count(*) from support_tickets where status::text in ('open','assigned','in_progress')",
        ),
        overdue_rent_dues=count_scalar(
            db,
            f"select count(*) from rent_dues {rent_where} {'and' if rent_where else 'where'} status::text = 'overdue'",
            rent_params,
        ),
        active_landlords=active_landlords,
        pending_landlord_requests=pending_landlord_requests,
        total_tenants=count_scalar(db, f"select count(*) from tenants {tenant_where}", tenant_params),
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
