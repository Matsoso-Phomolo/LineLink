```python
"""phase3f onboarding subscription rules

Revision ID: 20260601_0019
Revises: 20260531_0018
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260601_0019"
down_revision = "20260531_0018"
branch_labels = None
depends_on = None


def table_names(inspector) -> set[str]:
    return set(inspector.get_table_names())


def has_column(inspector, table: str, column: str) -> bool:
    return column in {item["name"] for item in inspector.get_columns(table)}


def has_unique_constraint(inspector, table: str, constraint_name: str) -> bool:
    return constraint_name in {
        item["name"] for item in inspector.get_unique_constraints(table)
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = table_names(inspector)

    if "landlord_request_properties" in tables:
        if not has_column(inspector, "landlord_request_properties", "single_rooms"):
            op.add_column(
                "landlord_request_properties",
                sa.Column("single_rooms", sa.Integer(), nullable=True),
            )

            op.execute(
                """
                update landlord_request_properties
                set single_rooms = coalesce(total_rooms, 1)
                where single_rooms is null
                """
            )

            op.alter_column(
                "landlord_request_properties",
                "single_rooms",
                nullable=False,
            )

        if not has_column(inspector, "landlord_request_properties", "double_rooms"):
            op.add_column(
                "landlord_request_properties",
                sa.Column("double_rooms", sa.Integer(), nullable=True),
            )

            op.execute(
                """
                update landlord_request_properties
                set double_rooms = 0
                where double_rooms is null
                """
            )

            op.alter_column(
                "landlord_request_properties",
                "double_rooms",
                nullable=False,
            )

        if not has_column(
            inspector,
            "landlord_request_properties",
            "single_room_prefix",
        ):
            op.add_column(
                "landlord_request_properties",
                sa.Column(
                    "single_room_prefix",
                    sa.String(length=20),
                    nullable=True,
                ),
            )

            op.execute(
                """
                update landlord_request_properties
                set single_room_prefix = 'A'
                where single_room_prefix is null
                """
            )

            op.alter_column(
                "landlord_request_properties",
                "single_room_prefix",
                nullable=False,
            )

        if not has_column(
            inspector,
            "landlord_request_properties",
            "double_room_prefix",
        ):
            op.add_column(
                "landlord_request_properties",
                sa.Column(
                    "double_room_prefix",
                    sa.String(length=20),
                    nullable=True,
                ),
            )

            op.execute(
                """
                update landlord_request_properties
                set double_room_prefix = 'B'
                where double_room_prefix is null
                """
            )

            op.alter_column(
                "landlord_request_properties",
                "double_room_prefix",
                nullable=False,
            )

        if not has_column(
            inspector,
            "landlord_request_properties",
            "starting_room_number",
        ):
            op.add_column(
                "landlord_request_properties",
                sa.Column(
                    "starting_room_number",
                    sa.Integer(),
                    nullable=True,
                ),
            )

            op.execute(
                """
                update landlord_request_properties
                set starting_room_number = 101
                where starting_room_number is null
                """
            )

            op.alter_column(
                "landlord_request_properties",
                "starting_room_number",
                nullable=False,
            )

    if "subscription_pricing_rules" not in tables:
        op.create_table(
            "subscription_pricing_rules",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "district_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("districts.id"),
                nullable=True,
            ),
            sa.Column(
                "tier_name",
                sa.String(length=80),
                nullable=False,
            ),
            sa.Column(
                "min_rooms",
                sa.Integer(),
                nullable=False,
            ),
            sa.Column(
                "max_rooms",
                sa.Integer(),
                nullable=True,
            ),
            sa.Column(
                "monthly_amount",
                sa.Numeric(12, 2),
                nullable=False,
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "created_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column(
                "updated_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "district_id",
                "tier_name",
                name="uq_sub_rule_district_tier",
            ),
        )

        op.create_index(
            "ix_sub_rules_district",
            "subscription_pricing_rules",
            ["district_id"],
        )

        op.create_index(
            "ix_sub_rules_tier",
            "subscription_pricing_rules",
            ["tier_name"],
        )

        op.create_index(
            "ix_sub_rules_active",
            "subscription_pricing_rules",
            ["is_active"],
        )

    if "district_admin_subscription_permissions" not in tables:
        op.create_table(
            "district_admin_subscription_permissions",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "district_admin_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "district_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("districts.id"),
                nullable=False,
            ),
            sa.Column(
                "can_manage_subscriptions",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "granted_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "district_admin_user_id",
                "district_id",
                name="uq_dasp_admin_district",
            ),
        )

        op.create_index(
            "ix_dasp_admin_user",
            "district_admin_subscription_permissions",
            ["district_admin_user_id"],
        )

        op.create_index(
            "ix_dasp_district",
            "district_admin_subscription_permissions",
            ["district_id"],
        )

        op.create_index(
            "ix_dasp_manage_subs",
            "district_admin_subscription_permissions",
            ["can_manage_subscriptions"],
        )

    if (
        "property_subscriptions" in tables
        and not has_unique_constraint(
            inspector,
            "property_subscriptions",
            "uq_property_subscriptions_property_id",
        )
    ):
        pass

    if "subscription_pricing_rules" in table_names(sa.inspect(bind)):
        op.execute(
            """
            insert into subscription_pricing_rules
                (
                    id,
                    district_id,
                    tier_name,
                    min_rooms,
                    max_rooms,
                    monthly_amount,
                    is_active,
                    created_at,
                    updated_at
                )
            select
                '00000000-0000-0000-0000-000000000151'::uuid,
                null,
                'rooms_1_to_15',
                1,
                15,
                50.00,
                true,
                now(),
                now()
            where not exists (
                select 1
                from subscription_pricing_rules
                where district_id is null
                and tier_name = 'rooms_1_to_15'
            )
            """
        )

        op.execute(
            """
            insert into subscription_pricing_rules
                (
                    id,
                    district_id,
                    tier_name,
                    min_rooms,
                    max_rooms,
                    monthly_amount,
                    is_active,
                    created_at,
                    updated_at
                )
            select
                '00000000-0000-0000-0000-000000000162'::uuid,
                null,
                'rooms_16_to_29',
                16,
                29,
                75.00,
                true,
                now(),
                now()
            where not exists (
                select 1
                from subscription_pricing_rules
                where district_id is null
                and tier_name = 'rooms_16_to_29'
            )
            """
        )

        op.execute(
            """
            insert into subscription_pricing_rules
                (
                    id,
                    district_id,
                    tier_name,
                    min_rooms,
                    max_rooms,
                    monthly_amount,
                    is_active,
                    created_at,
                    updated_at
                )
            select
                '00000000-0000-0000-0000-000000000303'::uuid,
                null,
                'rooms_30_plus',
                30,
                null,
                100.00,
                true,
                now(),
                now()
            where not exists (
                select 1
                from subscription_pricing_rules
                where district_id is null
                and tier_name = 'rooms_30_plus'
            )
            """
        )


def downgrade() -> None:
    pass
```
