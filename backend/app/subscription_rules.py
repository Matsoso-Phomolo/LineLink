from decimal import Decimal


def calculate_property_subscription_amount(total_rooms: int) -> tuple[Decimal, str]:
    if total_rooms <= 15:
        return Decimal("50.00"), "rooms_1_to_15"

    if total_rooms > 15 and total_rooms < 30:
        return Decimal("75.00"), "rooms_16_to_29"

    return Decimal("100.00"), "rooms_30_plus"
