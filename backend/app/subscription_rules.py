from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import SubscriptionPricingRule


DEFAULT_PRICING_RULES = (
    ("Starter Property Plan", 1, 15, Decimal("53.00")),
    ("Growth Property Plan", 16, 29, Decimal("78.00")),
    ("Enterprise Property Plan", 30, None, Decimal("103.00")),
)


def default_subscription_rules() -> list[dict[str, object]]:
    return [
        {
            "tier_name": tier_name,
            "min_rooms": min_rooms,
            "max_rooms": max_rooms,
            "monthly_amount": amount,
        }
        for tier_name, min_rooms, max_rooms, amount in DEFAULT_PRICING_RULES
    ]


def _matches(total_rooms: int, min_rooms: int, max_rooms: int | None) -> bool:
    return total_rooms >= min_rooms and (max_rooms is None or total_rooms <= max_rooms)


def calculate_property_subscription_amount(
    db: Session | None = None,
    *,
    district_id: UUID | None = None,
    total_rooms: int,
) -> tuple[Decimal, str]:
    if db is not None:
        for scoped_district_id in (district_id, None):
            rules = (
                db.query(SubscriptionPricingRule)
                .filter(
                    SubscriptionPricingRule.district_id == scoped_district_id,
                    SubscriptionPricingRule.is_active.is_(True),
                )
                .order_by(SubscriptionPricingRule.min_rooms.asc())
                .all()
            )
            for rule in rules:
                if _matches(total_rooms, rule.min_rooms, rule.max_rooms):
                    return Decimal(str(rule.monthly_amount)), rule.tier_name

    for tier_name, min_rooms, max_rooms, amount in DEFAULT_PRICING_RULES:
        if _matches(total_rooms, min_rooms, max_rooms):
            return amount, tier_name

    return Decimal("103.00"), "Enterprise Property Plan"
