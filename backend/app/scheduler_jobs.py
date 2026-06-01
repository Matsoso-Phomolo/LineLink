from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import PaymentTransaction, PaymentTransactionStatus
from app.reminders import run_reminders
from app.reservation_logic import clear_expired_rejection_messages, expire_stale_reservations


def run_operational_maintenance_jobs(db: Session) -> dict[str, int]:
    """Scheduler-compatible maintenance entrypoint.

    Render cron, a worker, or a future scheduler can call this safely. It does
    not perform destructive actions; it expires stale reservation/payment rows
    and delegates reminder generation to the existing reminder engine.
    """
    now = datetime.now(timezone.utc)
    expired_reservations = expire_stale_reservations(db, now)
    expired_rejection_messages = clear_expired_rejection_messages(db, now)
    timed_out_payments = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.status == PaymentTransactionStatus.pending,
            PaymentTransaction.created_at < now - timedelta(hours=2),
        )
        .update({PaymentTransaction.status: PaymentTransactionStatus.timeout}, synchronize_session=False)
    )
    reminder_result = run_reminders(db)
    db.commit()
    return {
        "expired_reservations": expired_reservations,
        "expired_rejection_messages": expired_rejection_messages,
        "timed_out_payments": timed_out_payments,
        "tenant_rent_reminders": int(reminder_result.get("tenant_rent_reminders", 0)),
        "subscription_reminders": int(reminder_result.get("subscription_reminders", 0)),
    }
