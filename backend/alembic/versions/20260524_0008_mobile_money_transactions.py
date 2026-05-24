"""add mobile money payment transactions

Revision ID: 20260524_0008
Revises: 20260524_0007
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260524_0008"
down_revision = "20260524_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if bind.dialect.name == "postgresql":
        status_enum = postgresql.ENUM("pending", "successful", "failed", "timeout", "pending_verification", name="payment_transaction_status", create_type=False)
        status_enum.create(bind, checkfirst=True)
        method_enum = postgresql.ENUM(name="payment_method", create_type=False)
    else:
        status_enum = sa.Enum("pending", "successful", "failed", "timeout", "pending_verification", name="payment_transaction_status")
        method_enum = sa.Enum("mpesa", "ecocash", "orange_money", "bank_transfer", "bank", "cash", name="payment_method")

    if "payment_transactions" not in tables:
        op.create_table(
            "payment_transactions",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("landlord_id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("rent_due_id", sa.UUID(), nullable=True),
            sa.Column("payment_submission_id", sa.UUID(), nullable=True),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("method", method_enum, nullable=False),
            sa.Column("payer_phone", sa.String(length=40), nullable=True),
            sa.Column("status", status_enum, nullable=False),
            sa.Column("idempotency_key", sa.String(length=160), nullable=False),
            sa.Column("checkout_request_id", sa.String(length=160), nullable=True),
            sa.Column("provider_reference", sa.String(length=160), nullable=True),
            sa.Column("provider_message", sa.Text(), nullable=True),
            sa.Column("provider_error", sa.Text(), nullable=True),
            sa.Column("raw_callback_json", sa.Text(), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["landlord_id"], ["landlords.id"]),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.ForeignKeyConstraint(["rent_due_id"], ["rent_dues.id"]),
            sa.ForeignKeyConstraint(["payment_submission_id"], ["payment_submissions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column, unique in (
            ("landlord_id", False),
            ("tenant_id", False),
            ("rent_due_id", False),
            ("payment_submission_id", False),
            ("method", False),
            ("status", False),
            ("idempotency_key", True),
            ("checkout_request_id", True),
            ("provider_reference", True),
        ):
            op.create_index(f"ix_payment_transactions_{column}", "payment_transactions", [column], unique=unique)


def downgrade() -> None:
    pass
