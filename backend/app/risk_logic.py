from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import RentDue, RentDueStatus, Tenant
from app.tenant_financial_logic import (
    calculate_tenant_balance,
    calculate_tenant_overdue_risk,
    calculate_tenant_payment_score,
)


def money(value) -> Decimal:
    return Decimal(value or 0)


def classify_financial_behavior(
    payment_score: int,
    overdue_count: int,
    max_days_overdue: int,
) -> str:
    if max_days_overdue >= 30 or payment_score < 40:
        return "critical"

    if max_days_overdue >= 14 or payment_score < 60:
        return "risky"

    if overdue_count > 0 or payment_score < 80:
        return "watchlist"

    return "stable"


def calculate_collection_probability(
    payment_score: int,
    overdue_count: int,
    max_days_overdue: int,
) -> float:
    probability = Decimal(payment_score)

    probability -= Decimal(overdue_count * 5)

    if max_days_overdue >= 7:
        probability -= Decimal("10")

    if max_days_overdue >= 14:
        probability -= Decimal("15")

    if max_days_overdue >= 30:
        probability -= Decimal("25")

    probability = max(Decimal("0"), min(Decimal("100"), probability))

    return float(round(probability, 2))


def predict_default_risk(
    payment_score: int,
    overdue_count: int,
    max_days_overdue: int,
    outstanding_balance: Decimal,
) -> str:
    if max_days_overdue >= 30 or outstanding_balance > 0 and payment_score < 45:
        return "critical"

    if max_days_overdue >= 14 or outstanding_balance > 0 and payment_score < 65:
        return "high"

    if overdue_count > 0 or outstanding_balance > 0:
        return "medium"

    return "low"


def generate_landlord_recommendation(
    behavior: str,
    default_risk: str,
    outstanding_balance: Decimal,
) -> str:
    if behavior == "critical" or default_risk == "critical":
        return "Escalate immediately, contact tenant directly, and require urgent payment follow-up."

    if behavior == "risky" or default_risk == "high":
        return "Send a warning reminder and monitor the tenant closely before extending future leniency."

    if behavior == "watchlist" or default_risk == "medium":
        return "Send a friendly payment reminder and continue monitoring payment consistency."

    if outstanding_balance > 0:
        return "Tenant has an outstanding balance. Send a normal reminder."

    return "Tenant appears financially stable. No immediate action required."


def generate_tenant_risk_summary(
    db: Session,
    tenant_id,
) -> dict:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    balance = calculate_tenant_balance(db, tenant_id)
    overdue = calculate_tenant_overdue_risk(db, tenant_id)
    score = calculate_tenant_payment_score(db, tenant_id)

    outstanding_balance = money(balance["outstanding_balance"])
    payment_score = int(score["payment_score"])
    overdue_count = int(overdue["overdue_count"])
    max_days_overdue = int(overdue["max_days_overdue"])

    behavior = classify_financial_behavior(
        payment_score=payment_score,
        overdue_count=overdue_count,
        max_days_overdue=max_days_overdue,
    )

    collection_probability = calculate_collection_probability(
        payment_score=payment_score,
        overdue_count=overdue_count,
        max_days_overdue=max_days_overdue,
    )

    default_risk = predict_default_risk(
        payment_score=payment_score,
        overdue_count=overdue_count,
        max_days_overdue=max_days_overdue,
        outstanding_balance=outstanding_balance,
    )

    recommendation = generate_landlord_recommendation(
        behavior=behavior,
        default_risk=default_risk,
        outstanding_balance=outstanding_balance,
    )

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant.full_name if tenant else None,
        "risk_level": behavior,
        "default_risk": default_risk,
        "collection_probability": collection_probability,
        "payment_score": payment_score,
        "outstanding_balance": outstanding_balance,
        "overdue_count": overdue_count,
        "max_days_overdue": max_days_overdue,
        "recommendation": recommendation,
    }
