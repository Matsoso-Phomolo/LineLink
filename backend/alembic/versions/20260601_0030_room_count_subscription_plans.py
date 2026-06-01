"""room count subscription plans

Revision ID: 20260601_0030
Revises: 20260601_0029
Create Date: 2026-06-01 00:30:00.000000
"""

from alembic import op


revision = "20260601_0030"
down_revision = "20260601_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter table subscription_plans add column if not exists min_rooms integer not null default 1")
    op.execute("alter table subscription_plans alter column max_rooms drop not null")
    op.execute(
        """
        insert into subscription_plans (id, name, min_rooms, max_rooms, monthly_price, max_properties, features, is_active, created_at, updated_at)
        values
            ('00000000-0000-0000-0000-00000000b001'::uuid, 'Starter Property Plan', 1, 15, 53, 1, 'For properties with 1-15 rooms', true, now(), now()),
            ('00000000-0000-0000-0000-00000000b002'::uuid, 'Growth Property Plan', 16, 29, 78, 1, 'For properties with 16-29 rooms', true, now(), now()),
            ('00000000-0000-0000-0000-00000000b003'::uuid, 'Enterprise Property Plan', 30, null, 103, 1, 'For properties with 30+ rooms', true, now(), now())
        on conflict (name) do update
        set
            min_rooms = excluded.min_rooms,
            max_rooms = excluded.max_rooms,
            monthly_price = excluded.monthly_price,
            max_properties = 1,
            features = excluded.features,
            is_active = true,
            updated_at = now()
        """
    )
    op.execute(
        """
        update subscription_pricing_rules
        set monthly_amount = case
            when min_rooms = 1 and max_rooms = 15 then 53
            when min_rooms = 16 and max_rooms = 29 then 78
            when min_rooms = 30 and max_rooms is null then 103
            else monthly_amount
        end
        """
    )


def downgrade() -> None:
    op.execute("alter table subscription_plans drop column if exists min_rooms")
