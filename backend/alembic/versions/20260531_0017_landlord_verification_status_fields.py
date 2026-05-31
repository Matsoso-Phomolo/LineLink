"""add landlord verification status and token fields

Revision ID: 20260531_0017
Revises: 20260531_0016
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "20260531_0017"
down_revision = "20260531_0016"
branch_labels = None
depends_on = None


def has_column(inspector, table: str, column: str) -> bool:
    return column in {item["name"] for item in inspector.get_columns(table)}


def has_index(inspector, table: str, index_name: str) -> bool:
    return index_name in {item["name"] for item in inspector.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if bind.dialect.name == "postgresql":
        for value in (
            "verification_requested",
            "verification_submitted",
            "ai_reviewed",
        ):
            op.execute(
                f"ALTER TYPE landlord_request_status ADD VALUE IF NOT EXISTS '{value}'"
            )

    if "landlord_requests" not in set(inspector.get_table_names()):
        return

    if not has_column(inspector, "landlord_requests", "verification_token"):
        op.add_column(
            "landlord_requests",
            sa.Column("verification_token", sa.String(length=255), nullable=True),
        )

    if not has_column(inspector, "landlord_requests", "verification_token_expires_at"):
        op.add_column(
            "landlord_requests",
            sa.Column("verification_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not has_index(inspector, "landlord_requests", "ix_landlord_requests_verification_token"):
        op.create_index(
            "ix_landlord_requests_verification_token",
            "landlord_requests",
            ["verification_token"],
            unique=True,
        )


def downgrade() -> None:
    pass
