from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import (
    LeaseAgreement,
    Notification,
    Occupancy,
    PaymentReceipt,
    PaymentSubmission,
    RentDue,
    SupportTicket,
    Tenant,
    User,
    UserRole,
)

router = APIRouter(prefix="/tenant-portal", tags=["tenant portal"])


def rows(db: Session, sql: str, params: dict[str, object]) -> list[dict[str, object]]:
    try:
        return [dict(row) for row in db.execute(text(sql), params).mappings().all()]
    except Exception:
        return []


def row(db: Session, sql: str, params: dict[str, object]) -> dict[str, object] | None:
    result = rows(db, sql, params)
    return result[0] if result else None


@router.get("/me")
def tenant_portal_me(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != UserRole.tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant portal is for tenant accounts only",
        )

    tenant = row(
        db,
        """
        select
            id,
            user_id,
            landlord_id,
            tenant_type::text as tenant_type,
            full_name,
            gender,
            phone,
            email,
            national_id,
            passport_number,
            student_number,
            institution,
            occupation,
            next_of_kin_name,
            next_of_kin_phone,
            emergency_contact_name,
            emergency_contact_phone,
            verification_status::text as verification_status,
            tenant_status::text as tenant_status,
            lease_start_date,
            lease_end_date,
            monthly_rent,
            deposit_amount,
            deposit_paid,
            outstanding_balance,
            notices,
            profile_photo_path,
            created_at
        from tenants
        where user_id = :user_id
        limit 1
        """,
        {"user_id": user.id},
    )

    if not tenant:
        return {
            "tenant": None,
            "occupancies": [],
            "rent_dues": [],
            "payments": [],
            "receipts": [],
            "leases": [],
            "support_tickets": [],
            "notifications": [],
        }

    tenant_id = tenant["id"]

    return {
        "tenant": tenant,
        "occupancies": rows(
            db,
            """
            select *, status::text as status
            from occupancies
            where tenant_id = :tenant_id
            order by created_at desc
            """,
            {"tenant_id": tenant_id},
        ),
        "rent_dues": rows(
            db,
            """
            select *, status::text as status
            from rent_dues
            where tenant_id = :tenant_id
            order by due_month desc
            """,
            {"tenant_id": tenant_id},
        ),
        "payments": rows(
            db,
            """
            select *, method::text as method, status::text as status
            from payment_submissions
            where tenant_id = :tenant_id
            order by created_at desc
            """,
            {"tenant_id": tenant_id},
        ),
        "receipts": rows(
            db,
            """
            select *, method::text as method
            from payment_receipts
            where tenant_id = :tenant_id
            order by issued_at desc
            """,
            {"tenant_id": tenant_id},
        ),
        "leases": rows(
            db,
            """
            select *, status::text as status
            from lease_agreements
            where tenant_id = :tenant_id
            order by created_at desc
            """,
            {"tenant_id": tenant_id},
        ),
        "support_tickets": rows(
            db,
            """
            select *, status::text as status
            from support_tickets
            where tenant_id = :tenant_id
            order by created_at desc
            """,
            {"tenant_id": tenant_id},
        ),
        "notifications": rows(
            db,
            """
            select *
            from notifications
            where user_id = :user_id
            order by created_at desc
            """,
            {"user_id": user.id},
        ),
    }
