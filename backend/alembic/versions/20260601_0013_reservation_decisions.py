"""add reservation decision metadata

Revision ID: 20260601_0013
Revises: 20260601_0012
Create Date: 2026-06-01 00:13:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_0013"
down_revision = "20260601_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("room_reservations", sa.Column("rejection_message", sa.Text(), nullable=True))
    op.add_column("room_reservations", sa.Column("rejection_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_room_reservations_rejection_expires_at"), "room_reservations", ["rejection_expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_room_reservations_rejection_expires_at"), table_name="room_reservations")
    op.drop_column("room_reservations", "rejection_expires_at")
    op.drop_column("room_reservations", "rejection_message")
