"""add districts table

Revision ID: add_districts_table
Revises: PUT_PREVIOUS_REVISION_ID_HERE
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260527_add_districts_table"
down_revision = "20260525_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "districts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rollout_stage", sa.String(length=80), nullable=False, server_default="locked"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_unique_constraint("uq_districts_name", "districts", ["name"])
    op.create_unique_constraint("uq_districts_slug", "districts", ["slug"])
    op.create_index("ix_districts_is_active", "districts", ["is_active"])
    op.create_index("ix_districts_slug", "districts", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_districts_slug", table_name="districts")
    op.drop_index("ix_districts_is_active", table_name="districts")
    op.drop_constraint("uq_districts_slug", "districts", type_="unique")
    op.drop_constraint("uq_districts_name", "districts", type_="unique")
    op.drop_table("districts")
