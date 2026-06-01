"""add room reservation payment workflow

Revision ID: 20260601_0012
Revises: 20260525_0011
Create Date: 2026-06-01 00:12:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260601_0012"
down_revision = "20260525_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE room_status ADD VALUE IF NOT EXISTS 'reserved'")

    reservation_status = postgresql.ENUM(
        "pending_landlord_review",
        "approved_for_payment",
        "payment_pending",
        "confirmed",
        "rejected",
        "expired",
        "cancelled",
        "completed",
        name="room_reservation_status",
        create_type=False,
    )
    reservation_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "room_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_seeker_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("landlord_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reservation_code", sa.String(length=80), nullable=False),
        sa.Column("status", reservation_status, nullable=False),
        sa.Column("reservation_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("reservation_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["tenant_applications.id"]),
        sa.ForeignKeyConstraint(["landlord_id"], ["landlords.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["payment_transactions.id"]),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"]),
        sa.ForeignKeyConstraint(["room_seeker_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_room_reservations_application_id"), "room_reservations", ["application_id"], unique=False)
    op.create_index(op.f("ix_room_reservations_landlord_id"), "room_reservations", ["landlord_id"], unique=False)
    op.create_index(op.f("ix_room_reservations_payment_id"), "room_reservations", ["payment_id"], unique=False)
    op.create_index(op.f("ix_room_reservations_property_id"), "room_reservations", ["property_id"], unique=False)
    op.create_index(op.f("ix_room_reservations_reservation_code"), "room_reservations", ["reservation_code"], unique=True)
    op.create_index(op.f("ix_room_reservations_reservation_expiry"), "room_reservations", ["reservation_expiry"], unique=False)
    op.create_index(op.f("ix_room_reservations_room_id"), "room_reservations", ["room_id"], unique=False)
    op.create_index(op.f("ix_room_reservations_room_seeker_id"), "room_reservations", ["room_seeker_id"], unique=False)
    op.create_index(op.f("ix_room_reservations_status"), "room_reservations", ["status"], unique=False)
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_room_active_reservation
        ON room_reservations(room_id)
        WHERE status IN ('pending_landlord_review', 'approved_for_payment', 'payment_pending', 'confirmed')
        """
    )

    op.add_column("payment_transactions", sa.Column("room_reservation_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_payment_transactions_room_reservation_id"), "payment_transactions", ["room_reservation_id"], unique=False)
    op.create_foreign_key("fk_payment_transactions_room_reservation_id", "payment_transactions", "room_reservations", ["room_reservation_id"], ["id"])
    op.add_column("payment_receipts", sa.Column("room_reservation_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_payment_receipts_room_reservation_id"), "payment_receipts", ["room_reservation_id"], unique=False)
    op.create_foreign_key("fk_payment_receipts_room_reservation_id", "payment_receipts", "room_reservations", ["room_reservation_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_payment_receipts_room_reservation_id", "payment_receipts", type_="foreignkey")
    op.drop_index(op.f("ix_payment_receipts_room_reservation_id"), table_name="payment_receipts")
    op.drop_column("payment_receipts", "room_reservation_id")
    op.drop_constraint("fk_payment_transactions_room_reservation_id", "payment_transactions", type_="foreignkey")
    op.drop_index(op.f("ix_payment_transactions_room_reservation_id"), table_name="payment_transactions")
    op.drop_column("payment_transactions", "room_reservation_id")
    op.execute("DROP INDEX IF EXISTS uq_room_active_reservation")
    op.drop_table("room_reservations")
    postgresql.ENUM(name="room_reservation_status").drop(op.get_bind(), checkfirst=True)
