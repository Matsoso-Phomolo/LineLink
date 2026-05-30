from decimal import Decimal

from sqlalchemy.orm import Session

from app.district_risk_logic import generate_district_risk_summary
from app.models import District, RentDue, RentDueStatus


def money(value) -> Decimal:
    return Decimal(value or 0)


def get_active_districts(db: Session) -> list[District]:
    return db.query(District).filter(District.is_active.is_(True)).all()


def calculate_national_collection_health(db: Session) -> dict:
    dues = db.query(RentDue).all()

    total_due = sum((money(due.amount_due) for due in dues), Decimal("0"))
    total_paid = sum((money(due.amount_paid) for due in dues), Decimal("0"))

    health = 100.0

    if total_due > 0:
        health = round(float((total_paid / total_due) * 100), 2)

    return {
        "total_due": total_due,
        "total_paid": total_paid,
        "national_collection_health": health,
    }


def calculate_national_risk_distribution(db: Session) -> dict:
    distribution = {
        "stable": 0,
        "watchlist": 0,
        "risky": 0,
        "critical": 0,
    }

    districts = get_active_districts(db)

    for district in districts:
        summary = generate_district_risk_summary(db, district.id)
        district_distribution = summary["risk_distribution"]

        for key in distribution:
            distribution[key] += district_distribution.get(key, 0)

    return distribution


def calculate_high_risk_districts(db: Session) -> list[dict]:
    districts = get_active_districts(db)
    high_risk: list[dict] = []

    for district in districts:
        summary = generate_district_risk_summary(db, district.id)

        risky_count = summary["risk_distribution"].get("risky", 0)
        critical_count = summary["risk_distribution"].get("critical", 0)

        if risky_count > 0 or critical_count > 0:
            high_risk.append(
                {
                    "district_id": district.id,
                    "district_name": district.name,
                    "district_collection_health": summary[
                        "district_collection_health"
                    ],
                    "overdue_count": summary["overdue_count"],
                    "overdue_exposure": summary["overdue_exposure"],
                    "risk_distribution": summary["risk_distribution"],
                }
            )

    return high_risk


def calculate_national_overdue_exposure(db: Session) -> dict:
    overdue_dues = (
        db.query(RentDue)
        .filter(RentDue.status == RentDueStatus.overdue)
        .all()
    )

    exposure = sum(
        (money(due.amount_due) - money(due.amount_paid) for due in overdue_dues),
        Decimal("0"),
    )

    return {
        "overdue_count": len(overdue_dues),
        "national_overdue_exposure": exposure,
    }


def generate_national_risk_summary(db: Session) -> dict:
    districts = get_active_districts(db)

    collection = calculate_national_collection_health(db)
    distribution = calculate_national_risk_distribution(db)
    high_risk_districts = calculate_high_risk_districts(db)
    overdue = calculate_national_overdue_exposure(db)

    national_risk_level = "stable"

    if distribution["critical"] > 0:
        national_risk_level = "critical"
    elif distribution["risky"] > 0:
        national_risk_level = "risky"
    elif distribution["watchlist"] > 0:
        national_risk_level = "watchlist"

    return {
        "total_districts": len(districts),
        "national_risk_level": national_risk_level,
        "national_collection_health": collection["national_collection_health"],
        "risk_distribution": distribution,
        "high_risk_districts": high_risk_districts,
        **overdue,
    }
