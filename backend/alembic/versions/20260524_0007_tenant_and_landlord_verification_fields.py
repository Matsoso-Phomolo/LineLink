"""add tenant account and landlord verification fields

Revision ID: 20260524_0007
Revises: 20260524_0006
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa

revision = "20260524_0007"
down_revision = "20260524_0006"
branch_labels = None
depends_on = None


def has_column(inspector, table: str, column: str) -> bool:
    return column in {item["name"] for item in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE landlord_request_status ADD VALUE IF NOT EXISTS 'under_review'")

    if "tenants" in tables:
        for name, column in [
            ("gender", sa.Column("gender", sa.String(length=80), nullable=True)),
            ("emergency_contact_name", sa.Column("emergency_contact_name", sa.String(length=255), nullable=True)),
            ("emergency_contact_phone", sa.Column("emergency_contact_phone", sa.String(length=40), nullable=True)),
        ]:
            if not has_column(inspector, "tenants", name):
                op.add_column("tenants", column)

    if "landlord_requests" in tables:
        for name, column in [
            ("national_id", sa.Column("national_id", sa.String(length=120), nullable=True)),
            ("selfie_path", sa.Column("selfie_path", sa.String(length=500), nullable=True)),
            ("ownership_proof_path", sa.Column("ownership_proof_path", sa.String(length=500), nullable=True)),
            ("utility_bill_path", sa.Column("utility_bill_path", sa.String(length=500), nullable=True)),
            ("ownership_document_path", sa.Column("ownership_document_path", sa.String(length=500), nullable=True)),
            ("village_location", sa.Column("village_location", sa.String(length=160), nullable=True)),
            ("number_of_properties", sa.Column("number_of_properties", sa.Integer(), nullable=True)),
            ("number_of_rooms", sa.Column("number_of_rooms", sa.Integer(), nullable=True)),
            ("emergency_contact", sa.Column("emergency_contact", sa.String(length=255), nullable=True)),
        ]:
            if not has_column(inspector, "landlord_requests", name):
                op.add_column("landlord_requests", column)


def downgrade() -> None:
    pass
