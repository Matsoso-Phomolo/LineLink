"""add available room status

Revision ID: 20260601_0023
Revises: 20260601_0022
Create Date: 2026-06-01 00:23:00.000000
"""

from alembic import op


revision = "20260601_0023"
down_revision = "20260601_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE room_status ADD VALUE IF NOT EXISTS 'available'")


def downgrade() -> None:
    pass
