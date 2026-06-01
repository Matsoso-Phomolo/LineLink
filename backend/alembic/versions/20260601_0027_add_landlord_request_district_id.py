"""add district ownership to landlord requests

Revision ID: 20260601_0027
Revises: 20260601_0026
Create Date: 2026-06-01 00:27:00.000000
"""

from alembic import op


revision = "20260601_0027"
down_revision = "20260601_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table landlord_requests add column if not exists district_id uuid")
    op.execute(
        """
        do $$
        begin
            if not exists (
                select 1
                from pg_constraint
                where conname = 'fk_landlord_requests_district_id'
            ) then
                alter table landlord_requests
                add constraint fk_landlord_requests_district_id
                foreign key (district_id) references districts(id);
            end if;
        end $$;
        """
    )
    op.execute(
        "create index if not exists ix_landlord_requests_district_id on landlord_requests (district_id)"
    )


def downgrade() -> None:
    op.execute("drop index if exists ix_landlord_requests_district_id")
    op.execute(
        "alter table landlord_requests drop constraint if exists fk_landlord_requests_district_id"
    )
    op.execute("alter table landlord_requests drop column if exists district_id")
