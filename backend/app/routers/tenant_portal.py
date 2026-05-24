from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Notification, Occupancy, PaymentSubmission, RentDue, SupportTicket, Tenant, User, UserRole

router = APIRouter(prefix="/tenant-portal", tags=["tenant portal"])


@router.get("/me")
def tenant_portal_me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != UserRole.tenant:
        return {"detail": "Tenant portal is for tenant accounts"}
    tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()
    if not tenant:
        return {"tenant": None, "occupancies": [], "rent_dues": [], "payments": [], "support_tickets": [], "notifications": []}
    return {
        "tenant": tenant,
        "occupancies": db.query(Occupancy).filter(Occupancy.tenant_id == tenant.id).all(),
        "rent_dues": db.query(RentDue).filter(RentDue.tenant_id == tenant.id).all(),
        "payments": db.query(PaymentSubmission).filter(PaymentSubmission.tenant_id == tenant.id).order_by(PaymentSubmission.created_at.desc()).all(),
        "support_tickets": db.query(SupportTicket).filter(SupportTicket.tenant_id == tenant.id).order_by(SupportTicket.created_at.desc()).all(),
        "notifications": db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).all(),
    }
