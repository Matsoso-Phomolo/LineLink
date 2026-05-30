from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Landlord, Property, RentDue, RentDueStatus
from app.portfolio_risk_logic import generate_landlord_portfolio_risk_summary


def money(value) -> Decimal:
    return Decimal(value or 0)


def get_district_landlords(
    db: Session,
    district_id,
) -> list[Landlord]:
    return (
        db.query(Landlord)
        .join(Property, Property.landlord_id == Landlord.id)
        .filter(Property.district_id == district_id)
        .distinct()
        .all()
    )


def calculate_district_collection_health(
    db: Session,
    district_id,
) -> dict:
    landlord_ids = [
        landlord.id
        for landlord in get_district_landlords(db, district_id)
    ]

    if not landlord_ids:
        return {
            "total_due": Decimal("0"),
            "total_paid": Decimal("0"),
            "district_collection_health": 100.0,
        }

    dues = (
        db.query(RentDue)
        .filter(RentDue.landlord_id.in_(landlord_ids))
        .all()
    )

    total_due = sum((money(due.amount_due) for due in dues), Decimal("0"))
    total_paid = sum((money(due.amount_paid) for due in dues), Decimal("0"))

    health = 100.0

    if total_due > 0:
        health = round(float((total_paid / total_due) * 100), 2)

    return {
        "total_due": total_due,
        "total_paid": total_paid,
        "district_collection_health": health,
    }


def calculate_district_risk_distribution(
    db: Session,
    district_id,
) -> dict:
    distribution = {
        "stable": 0,
        "watchlist": 0,
        "risky": 0,
        "critical": 0,
    }

    landlords = get_district_landlords(db, district_id)

    for landlord in landlords:
        summary = generate_landlord_portfolio_risk_summary(db, landlord.id)
        level = summary["portfolio_risk_level"]

        if level in distribution:
            distribution[level] += 1

    return distribution


def calculate_high_risk_landlords(
    db: Session,
    district_id,
) -> list[dict]:
    landlords = get_district_landlords(db, district_id)
    high_risk: list[dict] = []

    for landlord in landlords:
        summary = generate_landlord_portfolio_risk_summary(db, landlord.id)

        if summary["portfolio_risk_level"] in {"risky", "critical"}:
            high_risk.append(
                {
                    "landlord_id": landlord.id,
                    "business_name": landlord.business_name,
                    "portfolio_risk_level": summary["portfolio_risk_level"],
                    "risk_distribution": summary["risk_distribution"],
                    "collection_health": summary["collection_health"],
                }
            )

    return high_risk


def calculate_district_overdue_exposure(
    db: Session,
    district_id,
) -> dict:
    landlord_ids = [
        landlord.id
        for landlord in get_district_landlords(db, district_id)
    ]

    if not landlord_ids:
        return {
            "overdue_count": 0,
            "overdue_exposure": Decimal("0"),
        }

    overdue_dues = (
        db.query(RentDue)
        .filter(
            RentDue.landlord_id.in_(landlord_ids),
            RentDue.status == RentDueStatus.overdue,
        )
        .all()
    )

    overdue_exposure = sum(
        (money(due.amount_due) - money(due.amount_paid) for due in overdue_dues),
        Decimal("0"),
    )

    return {
        "overdue_count": len(overdue_dues),
        "overdue_exposure": overdue_exposure,
    }


def generate_district_risk_summary(
    db: Session,
    district_id,
) -> dict:
    landlords = get_district_landlords(db, district_id)
    collection = calculate_district_collection_health(db, district_id)
    distribution = calculate_district_risk_distribution(db, district_id)
    high_risk_landlords = calculate_high_risk_landlords(db, district_id)
    overdue = calculate_district_overdue_exposure(db, district_id)

    return {
        "district_id": district_id,
        "total_landlords": len(landlords),
        "district_collection_health": collection["district_collection_health"],
        "risk_distribution": distribution,
        "high_risk_landlords": high_risk_landlords,
        **overdue,
    }
