from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    PaymentMethod,
    PaymentReceipt,
    PaymentSubmission,
    RentDue,
)


def generate_receipt_number(
    landlord_id: str,
    payment_submission_id: str | None = None,
) -> str:
    landlord_short = landlord_id.replace("-", "")[:6].upper()

    if payment_submission_id:
        payment_short = payment_submission_id.replace("-", "")[:6].upper()
        return f"RL-RCT-{landlord_short}-{payment_short}"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"RL-RCT-{landlord_short}-{timestamp}"


def create_rent_payment_receipt(
    db: Session,
    due: RentDue,
    amount: Decimal,
    method: PaymentMethod,
    transaction_reference: str | None = None,
    payment_submission: PaymentSubmission | None = None,
) -> PaymentReceipt:
    existing_receipt = None

    if payment_submission:
        existing_receipt = (
            db.query(PaymentReceipt)
            .filter(PaymentReceipt.payment_submission_id == payment_submission.id)
            .first()
        )

    if existing_receipt:
        return existing_receipt

    receipt = PaymentReceipt(
        landlord_id=due.landlord_id,
        tenant_id=due.tenant_id,
        payment_submission_id=payment_submission.id if payment_submission else None,
        receipt_type="rent",
        receipt_number=generate_receipt_number(
            str(due.landlord_id),
            str(payment_submission.id) if payment_submission else None,
        ),
        amount=amount,
        method=method,
        transaction_reference=transaction_reference or due.payment_reference,
        issued_at=datetime.now(timezone.utc),
    )

    db.add(receipt)

    return receipt
