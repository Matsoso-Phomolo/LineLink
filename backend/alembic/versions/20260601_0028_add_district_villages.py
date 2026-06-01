"""add district villages

Revision ID: 20260601_0028
Revises: 20260601_0027
Create Date: 2026-06-01 00:28:00.000000
"""

from alembic import op


revision = "20260601_0028"
down_revision = "20260601_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        create table if not exists district_villages (
            id uuid primary key,
            area_id uuid not null references district_areas(id),
            name varchar(160) not null,
            slug varchar(220) not null unique,
            is_active boolean not null default true,
            description text,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )
    op.execute(
        "create index if not exists ix_district_villages_area_id on district_villages (area_id)"
    )
    op.execute(
        "create index if not exists ix_district_villages_is_active on district_villages (is_active)"
    )
    op.execute(
        """
        create unique index if not exists uq_district_villages_area_name
        on district_villages (area_id, lower(name))
        """
    )


def downgrade() -> None:
    op.execute("drop table if exists district_villages")
