"""add room request response privacy fields

Revision ID: 20260524_0009
Revises: 20260524_0008
Create Date: 2026-05-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260524_0009"
down_revision: Union[str, None] = "20260524_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


preferred_response_method = postgresql.ENUM("phone_call", "whatsapp", "email", "sms", name="preferred_response_method")
request_response_status = postgresql.ENUM("queued", "sent", "failed", "scaffolded", name="request_response_status")
call_task_status = postgresql.ENUM("pending_call", "contacted", "no_answer", name="call_task_status")
preferred_response_method_existing = postgresql.ENUM("phone_call", "whatsapp", "email", "sms", name="preferred_response_method", create_type=False)
request_response_status_existing = postgresql.ENUM("queued", "sent", "failed", "scaffolded", name="request_response_status", create_type=False)
call_task_status_existing = postgresql.ENUM("pending_call", "contacted", "no_answer", name="call_task_status", create_type=False)


def upgrade() -> None:
    op.execute("ALTER TYPE application_status ADD VALUE IF NOT EXISTS 'accepted'")
    op.execute("ALTER TYPE application_status ADD VALUE IF NOT EXISTS 'contacted'")
    bind = op.get_bind()
    preferred_response_method.create(bind, checkfirst=True)
    request_response_status.create(bind, checkfirst=True)
    call_task_status.create(bind, checkfirst=True)
    op.add_column("tenant_applications", sa.Column("preferred_response_method", preferred_response_method_existing, nullable=True))
    op.add_column("tenant_applications", sa.Column("response_contact_value", sa.String(length=255), nullable=True))
    op.add_column("tenant_applications", sa.Column("response_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenant_applications", sa.Column("response_status", request_response_status_existing, nullable=True))
    op.create_table(
        "request_response_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("recipient_name", sa.String(length=255), nullable=False),
        sa.Column("recipient_phone", sa.String(length=40), nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=True),
        sa.Column("channel", preferred_response_method_existing, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", request_response_status_existing, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["tenant_applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_request_response_logs_request_id"), "request_response_logs", ["request_id"], unique=False)
    op.create_index(op.f("ix_request_response_logs_channel"), "request_response_logs", ["channel"], unique=False)
    op.create_index(op.f("ix_request_response_logs_status"), "request_response_logs", ["status"], unique=False)
    op.create_table(
        "request_call_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("caller_user_id", sa.UUID(), nullable=False),
        sa.Column("recipient_phone", sa.String(length=40), nullable=False),
        sa.Column("status", call_task_status_existing, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["caller_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["tenant_applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_request_call_logs_request_id"), "request_call_logs", ["request_id"], unique=False)
    op.create_index(op.f("ix_request_call_logs_caller_user_id"), "request_call_logs", ["caller_user_id"], unique=False)
    op.create_index(op.f("ix_request_call_logs_status"), "request_call_logs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_request_call_logs_status"), table_name="request_call_logs")
    op.drop_index(op.f("ix_request_call_logs_caller_user_id"), table_name="request_call_logs")
    op.drop_index(op.f("ix_request_call_logs_request_id"), table_name="request_call_logs")
    op.drop_table("request_call_logs")
    op.drop_index(op.f("ix_request_response_logs_status"), table_name="request_response_logs")
    op.drop_index(op.f("ix_request_response_logs_channel"), table_name="request_response_logs")
    op.drop_index(op.f("ix_request_response_logs_request_id"), table_name="request_response_logs")
    op.drop_table("request_response_logs")
    op.drop_column("tenant_applications", "response_status")
    op.drop_column("tenant_applications", "response_sent_at")
    op.drop_column("tenant_applications", "response_contact_value")
    op.drop_column("tenant_applications", "preferred_response_method")
    call_task_status.drop(op.get_bind(), checkfirst=True)
    request_response_status.drop(op.get_bind(), checkfirst=True)
    preferred_response_method.drop(op.get_bind(), checkfirst=True)
