"""add professional rental operations fields

Revision ID: 20260524_0004
Revises: 20260524_0003
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260524_0004"
down_revision = "20260524_0003"
branch_labels = None
depends_on = None


def has_column(inspector, table: str, column: str) -> bool:
    return column in {item["name"] for item in inspector.get_columns(table)}


def has_index(inspector, table: str, index_name: str) -> bool:
    return index_name in {item["name"] for item in inspector.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if bind.dialect.name == "postgresql":
        for enum_name, values in {
            "rent_due_status": ("overdue",),
            "payment_method": ("orange_money", "bank_transfer"),
            "ticket_status": ("assigned",),
            "audit_action": ("REJECT_PAYMENT_SUBMISSION", "UPDATE_SUPPORT_TICKET", "APPROVE_LANDLORD"),
        }.items():
            for value in values:
                op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'")
        tenant_status = postgresql.ENUM("active", "overdue", "moved_out", "disabled", name="tenant_status", create_type=False)
        tenant_status.create(bind, checkfirst=True)
    else:
        tenant_status = sa.Enum("active", "overdue", "moved_out", "disabled", name="tenant_status")

    if "tenants" in tables:
        additions = [
            ("tenant_status", sa.Column("tenant_status", tenant_status, nullable=True, server_default="active")),
            ("lease_start_date", sa.Column("lease_start_date", sa.Date(), nullable=True)),
            ("lease_end_date", sa.Column("lease_end_date", sa.Date(), nullable=True)),
            ("monthly_rent", sa.Column("monthly_rent", sa.Numeric(12, 2), nullable=True)),
            ("deposit_amount", sa.Column("deposit_amount", sa.Numeric(12, 2), nullable=True)),
            ("deposit_paid", sa.Column("deposit_paid", sa.Boolean(), nullable=True, server_default=sa.false())),
            ("outstanding_balance", sa.Column("outstanding_balance", sa.Numeric(12, 2), nullable=True, server_default="0")),
            ("notices", sa.Column("notices", sa.Text(), nullable=True)),
        ]
        for name, column in additions:
            if not has_column(inspector, "tenants", name):
                op.add_column("tenants", column)
        if not has_index(inspector, "tenants", "ix_tenants_tenant_status"):
            op.create_index("ix_tenants_tenant_status", "tenants", ["tenant_status"])
        if not has_index(inspector, "tenants", "ix_tenants_deposit_paid"):
            op.create_index("ix_tenants_deposit_paid", "tenants", ["deposit_paid"])

    if "rent_dues" in tables:
        additions = [
            ("due_date", sa.Column("due_date", sa.Date(), nullable=True)),
            ("late_penalty_amount", sa.Column("late_penalty_amount", sa.Numeric(12, 2), nullable=True, server_default="0")),
            ("is_late", sa.Column("is_late", sa.Boolean(), nullable=True, server_default=sa.false())),
        ]
        for name, column in additions:
            if not has_column(inspector, "rent_dues", name):
                op.add_column("rent_dues", column)
        if not has_index(inspector, "rent_dues", "ix_rent_dues_is_late"):
            op.create_index("ix_rent_dues_is_late", "rent_dues", ["is_late"])
        op.execute("UPDATE rent_dues SET due_date = due_month WHERE due_date IS NULL")

    if "payment_receipts" not in tables:
        op.create_table(
            "payment_receipts",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("landlord_id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("payment_submission_id", sa.UUID(), nullable=False),
            sa.Column("receipt_number", sa.String(length=80), nullable=False),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("method", postgresql.ENUM(name="payment_method", create_type=False) if bind.dialect.name == "postgresql" else sa.Enum(name="payment_method"), nullable=False),
            sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("pdf_path", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["landlord_id"], ["landlords.id"]),
            sa.ForeignKeyConstraint(["payment_submission_id"], ["payment_submissions.id"]),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("payment_submission_id"),
            sa.UniqueConstraint("receipt_number"),
        )
        op.create_index("ix_payment_receipts_landlord_id", "payment_receipts", ["landlord_id"])
        op.create_index("ix_payment_receipts_payment_submission_id", "payment_receipts", ["payment_submission_id"], unique=True)
        op.create_index("ix_payment_receipts_receipt_number", "payment_receipts", ["receipt_number"], unique=True)
        op.create_index("ix_payment_receipts_tenant_id", "payment_receipts", ["tenant_id"])

    if "support_tickets" in tables:
        if not has_column(inspector, "support_tickets", "assigned_to_user_id"):
            op.add_column("support_tickets", sa.Column("assigned_to_user_id", sa.UUID(), nullable=True))
            op.create_foreign_key("fk_support_tickets_assigned_to_user_id_users", "support_tickets", "users", ["assigned_to_user_id"], ["id"])
        if not has_column(inspector, "support_tickets", "resolved_at"):
            op.add_column("support_tickets", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
        if not has_index(inspector, "support_tickets", "ix_support_tickets_assigned_to_user_id"):
            op.create_index("ix_support_tickets_assigned_to_user_id", "support_tickets", ["assigned_to_user_id"])


def downgrade() -> None:
    pass
