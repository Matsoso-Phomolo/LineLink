"""add district and area references to properties and listings

Revision ID: 20260528_0014
Revises: 20260528_0013
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260528_0014"
down_revision = "20260528_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "properties",
        sa.Column(
            "district_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.add_column(
        "properties",
        sa.Column(
            "area_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_properties_district_id",
        "properties",
        ["district_id"],
    )

    op.create_index(
        "ix_properties_area_id",
        "properties",
        ["area_id"],
    )

    op.create_foreign_key(
        "fk_properties_district_id",
        "properties",
        "districts",
        ["district_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_properties_area_id",
        "properties",
        "district_areas",
        ["area_id"],
        ["id"],
    )

    # ---------------------------------------------------

    op.add_column(
        "room_listings",
        sa.Column(
            "district_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.add_column(
        "room_listings",
        sa.Column(
            "area_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_room_listings_district_id",
        "room_listings",
        ["district_id"],
    )

    op.create_index(
        "ix_room_listings_area_id",
        "room_listings",
        ["area_id"],
    )

    op.create_foreign_key(
        "fk_room_listings_district_id",
        "room_listings",
        "districts",
        ["district_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_room_listings_area_id",
        "room_listings",
        "district_areas",
        ["area_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_room_listings_area_id",
        "room_listings",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_room_listings_district_id",
        "room_listings",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_room_listings_area_id",
        table_name="room_listings",
    )

    op.drop_index(
        "ix_room_listings_district_id",
        table_name="room_listings",
    )

    op.drop_column("room_listings", "area_id")
    op.drop_column("room_listings", "district_id")

    # ---------------------------------------------------

    op.drop_constraint(
        "fk_properties_area_id",
        "properties",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_properties_district_id",
        "properties",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_properties_area_id",
        table_name="properties",
    )

    op.drop_index(
        "ix_properties_district_id",
        table_name="properties",
    )

    op.drop_column("properties", "area_id")
    op.drop_column("properties", "district_id")
