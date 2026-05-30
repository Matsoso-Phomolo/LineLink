from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    PaymentReceipt,
    RentDue,
    RentDueStatus,
    Tenant,
)


def money(value) -> Decimal:
    return Decimal(value or 0)


def calculate_tenant_balance(
    db: Session,
    tenant_id,
) -> dict:
    dues = (
        db.query(RentDue)
        .filter(RentDue.tenant_id == tenant_id)
        .all()
    )

    total_due = sum((money(due.amount_due) for due in dues), Decimal("0"))
    total_paid = sum((money(due.amount_paid) for due in dues), Decimal("0"))
    outstanding_balance = total_due - total_paid

    return {
        "total_due": total_due,
        "total_paid": total_paid,
        "outstanding_balance": outstanding_balance,
    }


def calculate_tenant_payment_history(
    db: Session,
    tenant_id,
) -> dict:
    receipts = (
        db.query(PaymentReceipt)
        .filter(PaymentReceipt.tenant_id == tenant_id)
        .order_by(PaymentReceipt.issued_at.desc())
        .all()
    )

    total_receipts = len(receipts)
    total_paid = sum((money(receipt.amount) for receipt in receipts), Decimal("0"))

    return {
        "total_receipts": total_receipts,
        "total_paid": total_paid,
        "receipts": receipts,
    }


def calculate_tenant_overdue_risk(
    db: Session,
    tenant_id,
) -> dict:
    overdue_dues = (
        db.query(RentDue)
        .filter(
            RentDue.tenant_id == tenant_id,
            RentDue.status == RentDueStatus.overdue,
        )
        .all()
    )

    overdue_amount = sum(
        (money(due.amount_due) - money(due.amount_paid) for due in overdue_dues),
        Decimal("0"),
    )

    max_days_overdue = 0

    if overdue_dues:
        max_days_overdue = max(due.days_overdue or 0 for due in overdue_dues)

    risk_level = "low"

    if overdue_amount > 0:
        risk_level = "medium"

    if max_days_overdue >= 14:
        risk_level = "high"

    if max_days_overdue >= 30:
        risk_level = "critical"

    return {
        "overdue_count": len(overdue_dues),
        "overdue_amount": overdue_amount,
        "max_days_overdue": max_days_overdue,
        "risk_level": risk_level,
    }


def calculate_tenant_payment_score(
    db: Session,
    tenant_id,
) -> dict:
    dues = (
        db.query(RentDue)
        .filter(RentDue.tenant_id == tenant_id)
        .all()
    )

    if not dues:
        return {
            "payment_score": 100,
            "score_label": "new_tenant",
        }

    paid_dues = sum(1 for due in dues if due.status == RentDueStatus.paid)
    overdue_dues = sum(1 for due in dues if due.status == RentDueStatus.overdue)

    score = 100

    score -= overdue_dues * 15
    score += paid_dues * 3

    score = max(0, min(100, score))

    label = "excellent"

    if score < 80:
        label = "good"

    if score < 60:
        label = "risky"

    if score < 40:
        label = "high_risk"

    return {
        "payment_score": score,
        "score_label": label,
    }


def calculate_tenant_financial_summary(
    db: Session,
    tenant_id,
) -> dict:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    balance = calculate_tenant_balance(db, tenant_id)
    payment_history = calculate_tenant_payment_history(db, tenant_id)
    overdue_risk = calculate_tenant_overdue_risk(db, tenant_id)
    payment_score = calculate_tenant_payment_score(db, tenant_id)

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant.full_name if tenant else None,
        **balance,
        "payment_history": {
            "total_receipts": payment_history["total_receipts"],
            "total_paid": payment_history["total_paid"],
        },
        **overdue_risk,
        **payment_score,
    }
