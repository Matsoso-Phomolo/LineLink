"""tenant classification profile

Revision ID: 20260531_0018
Revises: 20260531_0017
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260531_0018"
down_revision = "20260531_0017"
branch_labels = None
depends_on = None


PROFILE_COLUMNS = [
    ("tenant_category", sa.String(length=40)),
    ("tenant_subtype", sa.String(length=80)),
    ("institution_name", sa.String(length=255)),
    ("sponsor_or_guardian_name", sa.String(length=255)),
    ("employer_or_business_name", sa.String(length=255)),
    ("work_location", sa.String(length=255)),
    ("number_of_occupants", sa.Integer()),
    ("children_count", sa.Integer()),
    ("parking_required", sa.Boolean()),
    ("funding_source", sa.String(length=255)),
    ("guarantor_name", sa.String(length=255)),
    ("additional_notes", sa.Text()),
]


def add_columns(table_name: str) -> None:
    for column_name, column_type in PROFILE_COLUMNS:
        op.add_column(table_name, sa.Column(column_name, column_type, nullable=True))


def drop_columns(table_name: str) -> None:
    for column_name, _ in reversed(PROFILE_COLUMNS):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    add_columns("tenants")
    add_columns("tenant_applications")

    op.execute(
        """
        update tenants
        set tenant_category = case
            when tenant_type::text = 'student' then 'student'
            else 'worker'
        end,
        tenant_subtype = case
            when tenant_type::text = 'student' then 'tertiary'
            else 'employed'
        end,
        institution_name = coalesce(institution_name, institution)
        where tenant_category is null
        """
    )
    op.execute(
        """
        update tenant_applications
        set tenant_category = case
            when tenant_type::text = 'student' then 'student'
            else 'worker'
        end,
        tenant_subtype = case
            when tenant_type::text = 'student' then 'tertiary'
            else 'employed'
        end,
        institution_name = coalesce(institution_name, institution)
        where tenant_category is null
        """
    )


def downgrade() -> None:
    drop_columns("tenant_applications")
    drop_columns("tenants")
