"""add application rejection cleanup fields

Revision ID: 20260602_0032
Revises: 20260602_0031
Create Date: 2026-06-02 00:32:00.000000
"""

from alembic import op


revision = "20260602_0032"
down_revision = "20260602_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table tenant_applications add column if not exists rejected_at timestamp with time zone")
    op.execute("alter table tenant_applications add column if not exists rejection_expires_at timestamp with time zone")
    op.execute("alter table tenant_applications add column if not exists deleted_at timestamp with time zone")
    op.execute("create index if not exists ix_tenant_applications_rejected_at on tenant_applications (rejected_at)")
    op.execute("create index if not exists ix_tenant_applications_rejection_expires_at on tenant_applications (rejection_expires_at)")
    op.execute("create index if not exists ix_tenant_applications_deleted_at on tenant_applications (deleted_at)")
    op.execute(
        """
        update tenant_applications
        set
            rejected_at = coalesce(rejected_at, updated_at, created_at, now()),
            rejection_expires_at = coalesce(rejection_expires_at, coalesce(updated_at, created_at, now()) + interval '60 minutes')
        where status::text = 'rejected'
          and rejected_at is null
        """
    )


def downgrade() -> None:
    pass
