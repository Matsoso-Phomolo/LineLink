from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    Occupancy,
    OccupancyStatus,
    RentDue,
    RentDueStatus,
)


def first_day(value: date) -> date:
    return date(value.year, value.month, 1)


def calculate_due_status(due: RentDue) -> RentDueStatus:
    amount_due = Decimal(due.amount_due or 0)
    amount_paid = Decimal(due.amount_paid or 0)

    if amount_paid >= amount_due:
        return RentDueStatus.paid

    if amount_paid > 0:
        return RentDueStatus.partial

    return RentDueStatus.unpaid


def generate_initial_rent_due(
    db: Session,
    occupancy: Occupancy,
) -> RentDue:
    due_month = first_day(occupancy.billing_start_month)

    existing_due = (
        db.query(RentDue)
        .filter(
            RentDue.occupancy_id == occupancy.id,
            RentDue.due_month == due_month,
        )
        .first()
    )

    if existing_due:
        refresh_due_status(existing_due)
        return existing_due

    due = RentDue(
        landlord_id=occupancy.landlord_id,
        tenant_id=occupancy.tenant_id,
        occupancy_id=occupancy.id,
        due_month=due_month,
        due_date=due_month,
        amount_due=occupancy.monthly_rent,
        amount_paid=Decimal("0"),
        status=RentDueStatus.unpaid,
    )

    db.add(due)

    return due


def generate_monthly_rent_dues(
    db: Session,
    target_month: date,
) -> list[RentDue]:
    due_month = first_day(target_month)

    active_occupancies = (
        db.query(Occupancy)
        .filter(Occupancy.status == OccupancyStatus.active)
        .all()
    )

    dues: list[RentDue] = []

    for occupancy in active_occupancies:
        existing_due = (
            db.query(RentDue)
            .filter(
                RentDue.occupancy_id == occupancy.id,
                RentDue.due_month == due_month,
            )
            .first()
        )

        if existing_due:
            refresh_due_status(existing_due)
            dues.append(existing_due)
            continue

        due = RentDue(
            landlord_id=occupancy.landlord_id,
            tenant_id=occupancy.tenant_id,
            occupancy_id=occupancy.id,
            due_month=due_month,
            due_date=due_month,
            amount_due=occupancy.monthly_rent,
            amount_paid=Decimal("0"),
            status=RentDueStatus.unpaid,
        )

        db.add(due)
        dues.append(due)

    return dues


def refresh_due_status(due: RentDue) -> None:
    today = date.today()

    due.is_late = bool(
        due.due_date
        and due.due_date < today
        and due.amount_paid < due.amount_due
    )

    if due.is_late and due.amount_paid < due.amount_due:
        due.status = RentDueStatus.overdue

    elif due.amount_paid <= 0:
        due.status = RentDueStatus.unpaid

    elif due.amount_paid < due.amount_due:
        due.status = RentDueStatus.partial

    else:
        due.status = RentDueStatus.paid
