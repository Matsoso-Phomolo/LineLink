"""add room occupancy fields

Revision ID: 20260601_0022
Revises: 20260601_0021
Create Date: 2026-06-01 00:22:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260601_0022"
down_revision = "20260601_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    rental_mode = postgresql.ENUM(
        "private",
        "family",
        "shared_student",
        "shared_general",
        "apartment",
        name="rental_mode",
        create_type=False,
    )
    rental_mode.create(op.get_bind(), checkfirst=True)
    op.add_column("rooms", sa.Column("occupancy_limit", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("rooms", sa.Column("max_people", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("rooms", sa.Column("rental_mode", rental_mode, nullable=False, server_default="private"))
    op.create_index(op.f("ix_rooms_occupancy_limit"), "rooms", ["occupancy_limit"], unique=False)
    op.create_index(op.f("ix_rooms_max_people"), "rooms", ["max_people"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_rooms_max_people"), table_name="rooms")
    op.drop_index(op.f("ix_rooms_occupancy_limit"), table_name="rooms")
    op.drop_column("rooms", "rental_mode")
    op.drop_column("rooms", "max_people")
    op.drop_column("rooms", "occupancy_limit")
    postgresql.ENUM(name="rental_mode").drop(op.get_bind(), checkfirst=True)
