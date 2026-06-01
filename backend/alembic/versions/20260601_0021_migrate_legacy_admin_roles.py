"""migrate legacy admin roles

Revision ID: 20260601_0021
Revises: 20260601_0020
Create Date: 2026-06-01 00:21:00.000000
"""

from alembic import op


revision = "20260601_0021"
down_revision = "20260601_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'national_admin'")
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'district_admin'")
    op.execute("UPDATE users SET role = 'national_admin' WHERE role = 'admin'")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'national_admin'")
