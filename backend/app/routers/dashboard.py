from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.models import ApplicationStatus, Landlord, LandlordRequest, LandlordRequestStatus, ListingStatus, Occupancy, OccupancyStatus, PaymentSubmission, PaymentSubmissionStatus, Property, RentDue, RentDueStatus, Room, RoomListing, RoomStatus, SupportTicket, Tenant, TenantApplication, TicketStatus, User, UserRole
from app.ownership import landlord_scope_filter
from app.schemas import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    props = landlord_scope_filter(db, user, Property)
    rooms = landlord_scope_filter(db, user, Room)
    scoped_applications = db.query(TenantApplication).join(RoomListing, TenantApplication.listing_id == RoomListing.id).filter(RoomListing.id.in_([l.id for l in landlord_scope_filter(db, user, RoomListing).all()]))
    return DashboardSummary(
        properties=props.count(),
        rooms=rooms.count(),
        vacant_rooms=rooms.filter(Room.status == RoomStatus.vacant).count(),
        occupied_rooms=rooms.filter(Room.status == RoomStatus.occupied).count(),
        active_tenants=landlord_scope_filter(db, user, Occupancy).filter(Occupancy.status == OccupancyStatus.active).count(),
        unpaid_rent_dues=landlord_scope_filter(db, user, RentDue).filter(RentDue.status.in_([RentDueStatus.unpaid, RentDueStatus.partial, RentDueStatus.overdue])).count(),
        pending_payment_submissions=landlord_scope_filter(db, user, PaymentSubmission).filter(PaymentSubmission.status == PaymentSubmissionStatus.pending).count(),
        published_listings=landlord_scope_filter(db, user, RoomListing).filter(RoomListing.status == ListingStatus.published).count(),
        pending_applications=scoped_applications.filter(
            TenantApplication.status.in_([ApplicationStatus.inquiry_pending, ApplicationStatus.form_sent, ApplicationStatus.submitted, ApplicationStatus.pending, ApplicationStatus.under_review, ApplicationStatus.info_requested]),
        ).count(),
        pending_room_requests=scoped_applications.filter(TenantApplication.status == ApplicationStatus.inquiry_pending).count(),
        maintenance_tickets=landlord_scope_filter(db, user, SupportTicket).filter(SupportTicket.status.in_([TicketStatus.open, TicketStatus.assigned, TicketStatus.in_progress])).count(),
        overdue_rent_dues=landlord_scope_filter(db, user, RentDue).filter(RentDue.status == RentDueStatus.overdue).count(),
        active_landlords=db.query(Landlord).filter(Landlord.is_active.is_(True)).count() if user.role == UserRole.admin else 0,
        pending_landlord_requests=db.query(LandlordRequest).filter(LandlordRequest.status == LandlordRequestStatus.pending).count() if user.role == UserRole.admin else 0,
        total_tenants=landlord_scope_filter(db, user, Tenant).count(),
    )
