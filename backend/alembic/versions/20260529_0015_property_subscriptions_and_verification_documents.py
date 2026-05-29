"""add property subscriptions and verification documents

Revision ID: 20260529_0015
Revises: 20260528_0014
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260529_0015"
down_revision = "20260528_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    verification_ai_recommendation = postgresql.ENUM(
        "approve",
        "reject",
        "manual_review",
        name="verification_ai_recommendation",
    )
    verification_ai_recommendation.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "landlord_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "landlord_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("landlord_requests.id"),
            nullable=False,
        ),
        sa.Column("national_id", sa.String(length=120), nullable=False),
        sa.Column("selfie_path", sa.String(length=500), nullable=True),
        sa.Column("utility_bill_path", sa.String(length=500), nullable=True),
        sa.Column("ownership_document_path", sa.String(length=500), nullable=True),
        sa.Column("business_registration_path", sa.String(length=500), nullable=True),
        sa.Column("additional_notes", sa.Text(), nullable=True),
        sa.Column(
            "ai_recommendation",
            postgresql.ENUM(
                "approve",
                "reject",
                "manual_review",
                name="verification_ai_recommendation",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("ai_confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("ai_risk_flags", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index(
        "ix_landlord_verifications_landlord_request_id",
        "landlord_verifications",
        ["landlord_request_id"],
        unique=True,
    )

    op.create_table(
        "landlord_verification_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "verification_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("landlord_verifications.id"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(length=80), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("ai_checked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ai_result", sa.Text(), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index(
        "ix_landlord_verification_documents_verification_id",
        "landlord_verification_documents",
        ["verification_id"],
    )

    op.create_index(
        "ix_landlord_verification_documents_document_type",
        "landlord_verification_documents",
        ["document_type"],
    )

    op.create_index(
        "ix_landlord_verification_documents_ai_checked",
        "landlord_verification_documents",
        ["ai_checked"],
    )

    op.create_table(
        "property_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "landlord_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("landlords.id"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id"),
            nullable=False,
        ),
        sa.Column("total_rooms", sa.Integer(), nullable=False),
        sa.Column("monthly_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("pricing_tier", sa.String(length=80), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active",
                "trialing",
                "past_due",
                "cancelled",
                name="subscription_status",
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index(
        "ix_property_subscriptions_landlord_id",
        "property_subscriptions",
        ["landlord_id"],
    )

    op.create_index(
        "ix_property_subscriptions_property_id",
        "property_subscriptions",
        ["property_id"],
        unique=True,
    )

    op.create_index(
        "ix_property_subscriptions_pricing_tier",
        "property_subscriptions",
        ["pricing_tier"],
    )

    op.create_index(
        "ix_property_subscriptions_status",
        "property_subscriptions",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_property_subscriptions_status", table_name="property_subscriptions")
    op.drop_index("ix_property_subscriptions_pricing_tier", table_name="property_subscriptions")
    op.drop_index("ix_property_subscriptions_property_id", table_name="property_subscriptions")
    op.drop_index("ix_property_subscriptions_landlord_id", table_name="property_subscriptions")
    op.drop_table("property_subscriptions")

    op.drop_index(
        "ix_landlord_verification_documents_ai_checked",
        table_name="landlord_verification_documents",
    )
    op.drop_index(
        "ix_landlord_verification_documents_document_type",
        table_name="landlord_verification_documents",
    )
    op.drop_index(
        "ix_landlord_verification_documents_verification_id",
        table_name="landlord_verification_documents",
    )
    op.drop_table("landlord_verification_documents")

    op.drop_index(
        "ix_landlord_verifications_landlord_request_id",
        table_name="landlord_verifications",
    )
    op.drop_table("landlord_verifications")

    verification_ai_recommendation = postgresql.ENUM(
        "approve",
        "reject",
        "manual_review",
        name="verification_ai_recommendation",
    )
    verification_ai_recommendation.drop(op.get_bind(), checkfirst=True)
