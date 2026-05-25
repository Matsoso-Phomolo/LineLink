"""add mopay transaction metadata and 2fa challenges

Revision ID: 20260525_0011
Revises: 20260525_0010
Create Date: 2026-05-25 00:11:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260525_0011"
down_revision = "20260525_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'mopay_mpesa'")
    op.execute("ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'mopay_ecocash'")
    op.execute("ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'mopay_card'")

    op.add_column("users", sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("preferred_2fa_channel", sa.String(length=40), nullable=False, server_default="email"))
    op.add_column("users", sa.Column("two_factor_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f("ix_users_two_factor_enabled"), "users", ["two_factor_enabled"], unique=False)
    op.create_index(op.f("ix_users_two_factor_required"), "users", ["two_factor_required"], unique=False)

    op.create_table(
        "two_factor_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_two_factor_challenges_channel"), "two_factor_challenges", ["channel"], unique=False)
    op.create_index(op.f("ix_two_factor_challenges_expires_at"), "two_factor_challenges", ["expires_at"], unique=False)
    op.create_index(op.f("ix_two_factor_challenges_status"), "two_factor_challenges", ["status"], unique=False)
    op.create_index(op.f("ix_two_factor_challenges_user_id"), "two_factor_challenges", ["user_id"], unique=False)

    op.alter_column("payment_transactions", "tenant_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.add_column("payment_transactions", sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("payment_transactions", sa.Column("payment_type", sa.String(length=60), nullable=False, server_default="rent"))
    op.add_column("payment_transactions", sa.Column("webhook_event_id", sa.String(length=160), nullable=True))
    op.add_column("payment_transactions", sa.Column("provider_status", sa.String(length=80), nullable=True))
    op.add_column("payment_transactions", sa.Column("verified_signature", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("payment_transactions", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payment_transactions", sa.Column("failure_reason", sa.Text(), nullable=True))
    op.create_foreign_key("fk_payment_transactions_subscription_id", "payment_transactions", "landlord_subscriptions", ["subscription_id"], ["id"])
    op.create_index(op.f("ix_payment_transactions_subscription_id"), "payment_transactions", ["subscription_id"], unique=False)
    op.create_index(op.f("ix_payment_transactions_payment_type"), "payment_transactions", ["payment_type"], unique=False)
    op.create_index(op.f("ix_payment_transactions_webhook_event_id"), "payment_transactions", ["webhook_event_id"], unique=True)
    op.create_index(op.f("ix_payment_transactions_provider_status"), "payment_transactions", ["provider_status"], unique=False)
    op.create_index(op.f("ix_payment_transactions_verified_signature"), "payment_transactions", ["verified_signature"], unique=False)

    op.alter_column("payment_receipts", "tenant_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.alter_column("payment_receipts", "payment_submission_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.add_column("payment_receipts", sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("payment_receipts", sa.Column("receipt_type", sa.String(length=40), nullable=False, server_default="rent"))
    op.create_foreign_key("fk_payment_receipts_subscription_id", "payment_receipts", "landlord_subscriptions", ["subscription_id"], ["id"])
    op.create_index(op.f("ix_payment_receipts_subscription_id"), "payment_receipts", ["subscription_id"], unique=False)
    op.create_index(op.f("ix_payment_receipts_receipt_type"), "payment_receipts", ["receipt_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_receipts_receipt_type"), table_name="payment_receipts")
    op.drop_index(op.f("ix_payment_receipts_subscription_id"), table_name="payment_receipts")
    op.drop_constraint("fk_payment_receipts_subscription_id", "payment_receipts", type_="foreignkey")
    op.drop_column("payment_receipts", "receipt_type")
    op.drop_column("payment_receipts", "subscription_id")
    op.alter_column("payment_receipts", "payment_submission_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("payment_receipts", "tenant_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)

    op.drop_index(op.f("ix_payment_transactions_verified_signature"), table_name="payment_transactions")
    op.drop_index(op.f("ix_payment_transactions_provider_status"), table_name="payment_transactions")
    op.drop_index(op.f("ix_payment_transactions_webhook_event_id"), table_name="payment_transactions")
    op.drop_index(op.f("ix_payment_transactions_payment_type"), table_name="payment_transactions")
    op.drop_index(op.f("ix_payment_transactions_subscription_id"), table_name="payment_transactions")
    op.drop_constraint("fk_payment_transactions_subscription_id", "payment_transactions", type_="foreignkey")
    op.drop_column("payment_transactions", "failure_reason")
    op.drop_column("payment_transactions", "processed_at")
    op.drop_column("payment_transactions", "verified_signature")
    op.drop_column("payment_transactions", "provider_status")
    op.drop_column("payment_transactions", "webhook_event_id")
    op.drop_column("payment_transactions", "payment_type")
    op.drop_column("payment_transactions", "subscription_id")
    op.alter_column("payment_transactions", "tenant_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)

    op.drop_index(op.f("ix_two_factor_challenges_user_id"), table_name="two_factor_challenges")
    op.drop_index(op.f("ix_two_factor_challenges_status"), table_name="two_factor_challenges")
    op.drop_index(op.f("ix_two_factor_challenges_expires_at"), table_name="two_factor_challenges")
    op.drop_index(op.f("ix_two_factor_challenges_channel"), table_name="two_factor_challenges")
    op.drop_table("two_factor_challenges")
    op.drop_index(op.f("ix_users_two_factor_required"), table_name="users")
    op.drop_index(op.f("ix_users_two_factor_enabled"), table_name="users")
    op.drop_column("users", "two_factor_required")
    op.drop_column("users", "preferred_2fa_channel")
    op.drop_column("users", "two_factor_enabled")
