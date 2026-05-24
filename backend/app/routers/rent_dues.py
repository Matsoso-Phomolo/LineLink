from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import RentDue, Tenant, User, UserRole
from app.ownership import landlord_scope_filter
from app.schemas import RentDueRead

router = APIRouter(prefix="/rent-dues", tags=["rent-dues"])


@router.get("", response_model=list[RentDueRead])
def list_rent_dues(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == UserRole.tenant:
        tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()
        if not tenant:
            return []
        return db.query(RentDue).filter(RentDue.tenant_id == tenant.id).order_by(RentDue.due_month.desc()).all()
    return landlord_scope_filter(db, user, RentDue).order_by(RentDue.due_month.desc()).all()
