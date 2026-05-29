from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import (
    get_actor_landlord_id,
    get_current_user,
    require_roles,
)
from app.models import AuditLog, Property, User, UserRole
from app.dependencies import (
    get_district_admin_district_ids,
    is_district_admin,
    is_national_admin,
)

router = APIRouter(prefix="/audit-logs", tags=["audit logs"])


@router.get("")
def list_audit_logs(
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
    if is_national_admin(user):
        return (
            db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(200)
            .all()
        )

    if is_district_admin(user):
        district_ids = get_district_admin_district_ids(db, user)

        if not district_ids:
            return []

        return (
            db.query(AuditLog)
            .join(Property, Property.landlord_id == AuditLog.landlord_id)
            .filter(Property.district_id.in_(district_ids))
            .distinct()
            .order_by(AuditLog.created_at.desc())
            .limit(200)
            .all()
        )

    landlord_id = get_actor_landlord_id(db, user)

    if not landlord_id:
        return []

    return (
        db.query(AuditLog)
        .filter(AuditLog.landlord_id == landlord_id)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )
