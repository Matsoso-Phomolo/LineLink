"""merge reservation and phase 3f migration heads

Revision ID: 20260601_0020
Revises: 20260601_0013, 20260601_0019
Create Date: 2026-06-01 00:20:00.000000
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision = "20260601_0020"
down_revision = ("20260601_0013", "20260601_0019")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
