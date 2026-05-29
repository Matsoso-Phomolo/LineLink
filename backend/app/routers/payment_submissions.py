import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit import log_action
from app.database import get_db
from app.dependencies import require_roles
from app.models import (
    AuditAction,
    Notification,
    Occupancy,
    PaymentReceipt,
    PaymentSubmission,
    PaymentSubmissionStatus,
    RentDue,
    Tenant,
    User,
    UserRole,
)
from app.ownership import get_tenant_in_scope, scoped_query
from app.rent_logic import refresh_due_status
from app.schemas import (
    PaymentReceiptRead,
    PaymentSubmissionCreate,
    PaymentSubmissionRead,
)

router = APIRouter(
    prefix="/payment-submissions",
    tags=["payment-submissions"],
)


def next_receipt_number(db: Session) -> str:
    sequence = db.query(PaymentReceipt).count() + 1

    while True:
        number = f"LL-RCPT-{sequence:06d}"

        if not db.query(PaymentReceipt).filter(
            PaymentReceipt.receipt_number == number
        ).first():
            return number

        sequence += 1


def submission_in_scope(
    db: Session,
    user: User,
    submission_id: uuid.UUID,
) -> PaymentSubmission:
    submission = (
        scoped_query(db, user, PaymentSubmission)
        .filter(PaymentSubmission.id == submission_id)
        .first()
    )

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment submission not found",
        )

    return submission


@router.post("", response_model=PaymentSubmissionRead)
def submit_payment(
    payload: PaymentSubmissionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
            UserRole.tenant,
        )
    ),
):
    tenant = get_tenant_in_scope(db, user, payload.tenant_id)

    duplicate = (
        db.query(PaymentSubmission)
        .filter(
            PaymentSubmission.landlord_id == tenant.landlord_id,
            PaymentSubmission.transaction_reference
            == payload.transaction_reference,
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate transaction reference",
        )

    submission = PaymentSubmission(
        **payload.model_dump(),
        landlord_id=tenant.landlord_id,
    )

    db.add(submission)

    log_action(
        db,
        AuditAction.create_payment,
        user,
        tenant.landlord_id,
        "PaymentSubmission",
    )

    db.commit()
    db.refresh(submission)

    return submission


@router.get("", response_model=list[PaymentSubmissionRead])
def list_payment_submissions(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    return (
        scoped_query(db, user, PaymentSubmission)
        .order_by(PaymentSubmission.created_at.desc())
        .all()
    )


@router.put(
    "/{submission_id}/approve",
    response_model=PaymentSubmissionRead,
)
def approve_submission(
    submission_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    submission = submission_in_scope(db, user, submission_id)

    submission.status = PaymentSubmissionStatus.approved
    submission.approved_by_user_id = user.id
    submission.approved_at = datetime.now(timezone.utc)

    due = None

    if submission.rent_due_id:
        due = db.get(RentDue, submission.rent_due_id)

        if due:
            due.amount_paid = float(due.amount_paid) + float(
                submission.amount
            )

            refresh_due_status(due)

            tenant = db.get(Tenant, due.tenant_id)

            if tenant:
                tenant.outstanding_balance = max(
                    0,
                    float(tenant.outstanding_balance or 0)
                    - float(submission.amount),
                )

    existing_receipt = (
        db.query(PaymentReceipt)
        .filter(
            PaymentReceipt.payment_submission_id == submission.id
        )
        .first()
    )

    if not existing_receipt:
        room_id = None

        if submission.rent_due_id and due:
            occupancy = db.get(Occupancy, due.occupancy_id)
            room_id = occupancy.room_id if occupancy else None

        db.add(
            PaymentReceipt(
                landlord_id=submission.landlord_id,
                tenant_id=submission.tenant_id,
                room_id=room_id,
                payment_submission_id=submission.id,
                receipt_number=next_receipt_number(db),
                amount=submission.amount,
                method=submission.method,
                transaction_reference=submission.transaction_reference,
                pdf_url=f"/payment-submissions/{submission.id}/receipt",
            )
        )

    tenant_for_notice = db.get(Tenant, submission.tenant_id)

    if tenant_for_notice and tenant_for_notice.user_id:
        db.add(
            Notification(
                user_id=tenant_for_notice.user_id,
                title="Payment approved",
                body=(
                    f"Payment "
                    f"{submission.transaction_reference} "
                    f"was approved and a receipt was generated."
                ),
                category="payments",
            )
        )

    log_action(
        db,
        AuditAction.approve_payment_submission,
        user,
        submission.landlord_id,
        "PaymentSubmission",
        submission.id,
    )

    db.commit()
    db.refresh(submission)

    return submission


@router.put(
    "/{submission_id}/reject",
    response_model=PaymentSubmissionRead,
)
def reject_submission(
    submission_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    submission = submission_in_scope(db, user, submission_id)

    submission.status = PaymentSubmissionStatus.rejected

    log_action(
        db,
        AuditAction.reject_payment_submission,
        user,
        submission.landlord_id,
        "PaymentSubmission",
        submission.id,
    )

    db.commit()
    db.refresh(submission)

    return submission


@router.get("/receipts", response_model=list[PaymentReceiptRead])
def list_receipts(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    return (
        scoped_query(db, user, PaymentReceipt)
        .order_by(PaymentReceipt.created_at.desc())
        .all()
    )
