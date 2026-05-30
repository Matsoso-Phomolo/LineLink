from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    PaymentMethod,
    PaymentSubmission,
    RentDue,
)
from app.receipt_logic import create_rent_payment_receipt
from app.rent_logic import refresh_due_status


def find_due_by_reference(
    db: Session,
    payment_reference: str,
) -> RentDue:
    due = (
        db.query(RentDue)
        .filter(RentDue.payment_reference == payment_reference)
        .first()
    )

    if not due:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rent due found for this payment reference.",
        )

    return due


def allocate_payment_to_due(
    db: Session,
    due: RentDue,
    amount: Decimal,
    method: PaymentMethod,
    transaction_reference: str | None = None,
    payment_submission: PaymentSubmission | None = None,
) -> RentDue:
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be greater than zero.",
        )

    due.amount_paid = Decimal(due.amount_paid or 0) + amount

    refresh_due_after_payment(due)

    create_rent_payment_receipt(
        db=db,
        due=due,
        amount=amount,
        method=method,
        transaction_reference=transaction_reference,
        payment_submission=payment_submission,
    )

    db.flush()

    return due


def refresh_due_after_payment(due: RentDue) -> None:
    refresh_due_status(due)
