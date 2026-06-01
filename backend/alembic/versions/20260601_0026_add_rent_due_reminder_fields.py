"""add rent due reminder fields

Revision ID: 20260601_0026
Revises: 20260601_0025
Create Date: 2026-06-01 00:26:00.000000
"""

from alembic import op


revision = "20260601_0026"
down_revision = "20260601_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table rent_dues add column if not exists payment_reference varchar(120)")
    op.execute("alter table rent_dues add column if not exists days_overdue integer not null default 0")
    op.execute("alter table rent_dues add column if not exists last_reminder_sent_at timestamptz")
    op.execute("alter table rent_dues add column if not exists reminder_count integer not null default 0")
    op.execute("create unique index if not exists ix_rent_dues_payment_reference on rent_dues (payment_reference)")


def downgrade() -> None:
    pass
