"""add identity usernames rules complaints and categories

Revision ID: 20260524_0005
Revises: 20260524_0004
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260524_0005"
down_revision = "20260524_0004"
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

    if "users" in tables:
        if not has_column(inspector, "users", "username"):
            op.add_column("users", sa.Column("username", sa.String(length=80), nullable=True))
        if not has_column(inspector, "users", "must_change_password"):
            op.add_column("users", sa.Column("must_change_password", sa.Boolean(), nullable=True, server_default=sa.false()))
        if not has_index(inspector, "users", "ix_users_username"):
            op.create_index("ix_users_username", "users", ["username"], unique=True)
        if not has_index(inspector, "users", "ix_users_must_change_password"):
            op.create_index("ix_users_must_change_password", "users", ["must_change_password"])

    if bind.dialect.name == "postgresql":
        rule_visibility = postgresql.ENUM("public", "private", name="rule_visibility", create_type=False)
        complaint_visibility = postgresql.ENUM("public", "private", name="complaint_visibility", create_type=False)
        complaint_status = postgresql.ENUM("open", "in_review", "resolved", name="complaint_status", create_type=False)
        for enum_type in (rule_visibility, complaint_visibility, complaint_status):
            enum_type.create(bind, checkfirst=True)
    else:
        rule_visibility = sa.Enum("public", "private", name="rule_visibility")
        complaint_visibility = sa.Enum("public", "private", name="complaint_visibility")
        complaint_status = sa.Enum("open", "in_review", "resolved", name="complaint_status")

    if "property_categories" not in tables:
        op.create_table(
            "property_categories",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("landlord_id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["landlord_id"], ["landlords.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("landlord_id", "name", name="uq_property_category_landlord_name"),
        )
        op.create_index("ix_property_categories_landlord_id", "property_categories", ["landlord_id"])

    for table in ("properties", "rooms"):
        if table in tables and not has_column(inspector, table, "category_id"):
            op.add_column(table, sa.Column("category_id", sa.UUID(), nullable=True))
            op.create_foreign_key(f"fk_{table}_category_id_property_categories", table, "property_categories", ["category_id"], ["id"])
            op.create_index(f"ix_{table}_category_id", table, ["category_id"])

    if "room_listings" in tables and not has_column(inspector, "room_listings", "is_verified"):
        op.add_column("room_listings", sa.Column("is_verified", sa.Boolean(), nullable=True, server_default=sa.false()))
        op.create_index("ix_room_listings_is_verified", "room_listings", ["is_verified"])

    if "line_rules" not in tables:
        op.create_table(
            "line_rules",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("landlord_id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("visibility", rule_visibility, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["landlord_id"], ["landlords.id"]),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_line_rules_landlord_id", "line_rules", ["landlord_id"])
        op.create_index("ix_line_rules_tenant_id", "line_rules", ["tenant_id"])
        op.create_index("ix_line_rules_visibility", "line_rules", ["visibility"])

    if "rule_acknowledgements" not in tables:
        op.create_table(
            "rule_acknowledgements",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("rule_id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["rule_id"], ["line_rules.id"]),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("rule_id", "tenant_id", name="uq_rule_acknowledgement"),
        )
        op.create_index("ix_rule_acknowledgements_rule_id", "rule_acknowledgements", ["rule_id"])
        op.create_index("ix_rule_acknowledgements_tenant_id", "rule_acknowledgements", ["tenant_id"])

    if "complaints" not in tables:
        op.create_table(
            "complaints",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("landlord_id", sa.UUID(), nullable=True),
            sa.Column("sender_user_id", sa.UUID(), nullable=False),
            sa.Column("receiver_user_id", sa.UUID(), nullable=True),
            sa.Column("property_id", sa.UUID(), nullable=True),
            sa.Column("room_id", sa.UUID(), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("visibility", complaint_visibility, nullable=False),
            sa.Column("status", complaint_status, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["landlord_id"], ["landlords.id"]),
            sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
            sa.ForeignKeyConstraint(["receiver_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["room_id"], ["rooms.id"]),
            sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("landlord_id", "sender_user_id", "receiver_user_id", "property_id", "room_id", "visibility", "status"):
            op.create_index(f"ix_complaints_{column}", "complaints", [column])

    if "password_reset_tokens" not in tables:
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("token", sa.String(length=160), nullable=False),
            sa.Column("channel", sa.String(length=40), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
        op.create_index("ix_password_reset_tokens_token", "password_reset_tokens", ["token"], unique=True)
        op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])


def downgrade() -> None:
    pass
