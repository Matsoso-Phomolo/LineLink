"""add occupancy slot number column

Revision ID: 20260601_0025
Revises: 20260601_0024
Create Date: 2026-06-01 00:25:00.000000
"""

from alembic import op


revision = "20260601_0025"
down_revision = "20260601_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        alter table occupancies
        add column if not exists occupancy_slot_number integer not null default 1
        """
    )
    op.execute(
        """
        create index if not exists ix_occupancies_occupancy_slot_number
        on occupancies (occupancy_slot_number)
        """
    )


def downgrade() -> None:
    pass
