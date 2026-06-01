"""add manual landlord audit action

Revision ID: 20260601_0029
Revises: 20260601_0028
Create Date: 2026-06-01 00:29:00.000000
"""

from alembic import op


revision = "20260601_0029"
down_revision = "20260601_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        begin
            alter type audit_action add value if not exists 'DISTRICT_ADMIN_MANUAL_LANDLORD_CREATED';
        exception
            when undefined_object then null;
        end $$;
        """
    )


def downgrade() -> None:
    pass
