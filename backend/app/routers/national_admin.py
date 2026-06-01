import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.database import get_db
from app.dependencies import require_roles
from app.identity import first_name_password, first_name_username
from app.models import District, DistrictAdminAssignment, User, UserRole
from app.reminders import run_reminders

router = APIRouter(prefix="/admin", tags=["national admin"])
logger = logging.getLogger(__name__)


def empty_ai_risk_center(reason: str | None = None) -> dict[str, object]:
    return {
        "decision_support_only": True,
        "landlord_risk_cards": [],
        "listing_fraud_cards": [],
        "complaint_severity_cards": [],
        "suspicious_payment_alerts": [],
        "daily_admin_summary": {
            "new_landlord_requests": 0,
            "pending_listing_verification": 0,
            "overdue_subscriptions": 0,
            "unresolved_complaints": 0,
            "open_maintenance_tickets": 0,
            "recent_failed_payments": 0,
            "reminders_scaffolded": 0,
            "rejected_payment_proofs": 0,
        },
        "status": "degraded" if reason else "ok",
        "message": reason,
    }


class DistrictAdminCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    district_id: uuid.UUID


class DistrictAdminUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    district_id: uuid.UUID | None = None
    is_active: bool | None = None


class DistrictAdminRead(BaseModel):
    id: uuid.UUID
    username: str | None = None
    temporary_password: str | None = None
    full_name: str
    email: str
    phone: str | None = None
    role: UserRole
    is_active: bool
    district_id: uuid.UUID
    district_name: str

    class Config:
        from_attributes = True


@router.post("/run-reminders")
def run_platform_reminders(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    return run_reminders(db)


@router.get("/subscription-analytics/districts")
def subscription_analytics_by_district(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    rows = db.execute(
        text(
            """
            select
                d.id as district_id,
                d.name as district_name,
                count(distinct p.landlord_id) as total_landlords,
                count(distinct case when ps.status::text = 'active' then p.landlord_id end) as paid_landlords,
                count(distinct case when ps.id is null or ps.status::text <> 'active' then p.landlord_id end) as unpaid_landlords,
                count(case when ps.status::text = 'active' then 1 end) as active_subscriptions,
                count(case when ps.status::text = 'past_due' then 1 end) as pending_subscriptions,
                count(case when ps.status::text = 'cancelled' then 1 end) as expired_subscriptions,
                coalesce(sum(ps.monthly_amount), 0) as expected_amount,
                coalesce((
                    select sum(pt.amount)
                    from payment_transactions pt
                    join properties pp on pp.landlord_id = pt.landlord_id
                    where pp.district_id = d.id
                    and pt.payment_type = 'landlord_subscription'
                    and pt.status::text = 'successful'
                ), 0) as collected_amount
            from districts d
            left join properties p on p.district_id = d.id
            left join property_subscriptions ps on ps.property_id = p.id
            group by d.id, d.name
            order by d.name asc
            """
        )
    ).mappings().all()

    districts = [dict(row) for row in rows]
    return {
        "districts": districts,
        "totals": {
            "total_landlords": sum(int(row["total_landlords"] or 0) for row in districts),
            "total_paid_landlords": sum(int(row["paid_landlords"] or 0) for row in districts),
            "total_unpaid_landlords": sum(int(row["unpaid_landlords"] or 0) for row in districts),
            "total_expected_amount": sum(float(row["expected_amount"] or 0) for row in districts),
            "total_collected_amount": sum(float(row["collected_amount"] or 0) for row in districts),
        },
    }


@router.get("/ai-risk-center")
def ai_risk_center(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    return empty_ai_risk_center(
        "National Admin landlord risk access has moved to District Admins."
    )


@router.post("/district-admins", response_model=DistrictAdminRead)
def create_district_admin(
    payload: DistrictAdminCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    district = db.get(District, payload.district_id)

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found",
        )

    email = str(payload.email).strip().lower()
    phone = payload.phone.strip() if payload.phone else None
    full_name = payload.full_name.strip()
    username = first_name_username(full_name)
    password = first_name_password(full_name)

    existing_user = db.query(User).filter(User.email == email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    if phone:
        existing_phone = db.query(User).filter(User.phone == phone).first()

        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this phone number already exists",
            )

    existing_username = db.query(User).filter(User.username == username).first()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The autogenerated username '{username}' already exists",
        )

    district_admin = User(
        username=username,
        email=email,
        phone=phone,
        full_name=full_name,
        role=UserRole.district_admin,
        hashed_password=get_password_hash(password),
        is_active=True,
        must_change_password=False,
    )

    try:
        db.add(district_admin)
        db.flush()

        assignment = DistrictAdminAssignment(
            user_id=district_admin.id,
            district_id=district.id,
            is_active=True,
        )

        db.add(assignment)
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.exception("District Admin creation failed because of duplicate data")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="District Admin could not be created because the email, phone, username, or district assignment already exists.",
        ) from None
    except Exception:
        db.rollback()
        logger.exception("District Admin creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="District Admin could not be created. Please try again or check backend logs.",
        ) from None

    db.refresh(district_admin)
    db.refresh(assignment)

    return DistrictAdminRead(
        id=district_admin.id,
        username=district_admin.username,
        temporary_password=password,
        full_name=district_admin.full_name,
        email=district_admin.email,
        phone=district_admin.phone,
        role=district_admin.role,
        is_active=district_admin.is_active,
        district_id=district.id,
        district_name=district.name,
    )


@router.get("/district-admins", response_model=list[DistrictAdminRead])
def list_district_admins(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    rows = (
        db.query(User, DistrictAdminAssignment, District)
        .join(DistrictAdminAssignment, DistrictAdminAssignment.user_id == User.id)
        .join(District, District.id == DistrictAdminAssignment.district_id)
        .filter(User.role == UserRole.district_admin)
        .order_by(District.name.asc(), User.full_name.asc())
        .all()
    )

    return [
        DistrictAdminRead(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            is_active=user.is_active and assignment.is_active,
            district_id=district.id,
            district_name=district.name,
        )
        for user, assignment, district in rows
    ]


@router.post("/district-admins/{user_id}/disable")
def disable_district_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    user = db.get(User, user_id)

    if not user or user.role != UserRole.district_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District admin not found",
        )

    user.is_active = False

    db.query(DistrictAdminAssignment).filter(
        DistrictAdminAssignment.user_id == user.id
    ).update({"is_active": False})

    db.commit()

    return {"detail": "District admin disabled"}


@router.post("/district-admins/{user_id}/enable")
def enable_district_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    user = db.get(User, user_id)

    if not user or user.role != UserRole.district_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District admin not found",
        )

    user.is_active = True

    db.query(DistrictAdminAssignment).filter(
        DistrictAdminAssignment.user_id == user.id
    ).update({"is_active": True})

    db.commit()

    return {"detail": "District admin enabled"}


@router.patch("/district-admins/{user_id}", response_model=DistrictAdminRead)
def update_district_admin(
    user_id: uuid.UUID,
    payload: DistrictAdminUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    user = db.get(User, user_id)

    if not user or user.role != UserRole.district_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District admin not found",
        )

    assignment = (
        db.query(DistrictAdminAssignment)
        .filter(DistrictAdminAssignment.user_id == user.id)
        .first()
    )

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District admin assignment not found",
        )

    if payload.email and payload.email != user.email:
        existing_email = db.query(User).filter(User.email == payload.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )
        user.email = payload.email

    if payload.phone is not None and payload.phone != user.phone:
        if payload.phone:
            existing_phone = db.query(User).filter(User.phone == payload.phone).first()
            if existing_phone and existing_phone.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A user with this phone number already exists",
                )
        user.phone = payload.phone

    if payload.full_name is not None:
        user.full_name = payload.full_name

    if payload.district_id is not None:
        district = db.get(District, payload.district_id)
        if not district:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="District not found",
            )
        assignment.district_id = district.id
    else:
        district = db.get(District, assignment.district_id)

    if payload.is_active is not None:
        user.is_active = payload.is_active
        assignment.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    db.refresh(assignment)
    district = db.get(District, assignment.district_id)

    return DistrictAdminRead(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active and assignment.is_active,
        district_id=assignment.district_id,
        district_name=district.name if district else "Unknown district",
    )


@router.delete("/district-admins/{user_id}")
def delete_district_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    user = db.get(User, user_id)

    if not user or user.role != UserRole.district_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District admin not found",
        )

    db.query(DistrictAdminAssignment).filter(
        DistrictAdminAssignment.user_id == user.id
    ).delete()
    db.delete(user)
    db.commit()

    return {"detail": "District admin deleted"}
