"""assign Maseru operations to Theresia district admin

Revision ID: 20260601_0024
Revises: 20260601_0023
Create Date: 2026-06-01 00:24:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_0024"
down_revision = "20260601_0023"
branch_labels = None
depends_on = None


MASERU_DISTRICT_ID = "00000000-0000-0000-0000-00000000a001"
ROMA_AREA_ID = "00000000-0000-0000-0000-00000000a002"
THERESIA_USER_ID = "00000000-0000-0000-0000-00000000a003"
THERESIA_ASSIGNMENT_ID = "00000000-0000-0000-0000-00000000a004"
THERESIA_HASH = "$2b$12$rg5MVhLgLbenfWBiAgFg5OfcWCXqZkretnG6fw534tRLjLkAG4lXu"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    assignment_columns = {
        column["name"] for column in inspector.get_columns("district_admin_assignments")
    }

    if "is_active" not in assignment_columns:
        op.add_column(
            "district_admin_assignments",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.create_index(
            "ix_district_admin_assignments_is_active",
            "district_admin_assignments",
            ["is_active"],
        )

    if "updated_at" not in assignment_columns:
        op.add_column(
            "district_admin_assignments",
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    op.execute(
        sa.text(
            f"""
            insert into districts (
                id,
                name,
                slug,
                is_active,
                rollout_stage,
                description,
                activated_at,
                created_at,
                updated_at
            )
            values (
                '{MASERU_DISTRICT_ID}',
                'Maseru',
                'maseru',
                true,
                'active',
                'Active district managed by THERESIA KALAKA.',
                now(),
                now(),
                now()
            )
            on conflict (name) do update
            set
                is_active = true,
                rollout_stage = 'active',
                activated_at = coalesce(districts.activated_at, now()),
                updated_at = now()
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            insert into district_areas (
                id,
                district_id,
                name,
                slug,
                is_active,
                description,
                created_at,
                updated_at
            )
            select
                '{ROMA_AREA_ID}',
                id,
                'Roma',
                'roma',
                true,
                'Roma area under Maseru district.',
                now(),
                now()
            from districts
            where slug = 'maseru'
            on conflict do nothing
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            do $$
            declare
                maseru_id uuid;
                theresia_id uuid;
            begin
                select id into maseru_id
                from districts
                where slug = 'maseru'
                limit 1;

                select id into theresia_id
                from users
                where lower(email) = 'motebang@gmail.com'
                   or username = 'theresia'
                   or lower(full_name) = 'theresia kalaka'
                order by created_at asc
                limit 1;

                if theresia_id is null then
                    theresia_id := '{THERESIA_USER_ID}'::uuid;

                    insert into users (
                        id,
                        username,
                        email,
                        phone,
                        full_name,
                        hashed_password,
                        role,
                        is_active,
                        must_change_password,
                        two_factor_enabled,
                        preferred_2fa_channel,
                        two_factor_required,
                        created_at,
                        updated_at
                    )
                    values (
                        theresia_id,
                        'theresia',
                        'motebang@gmail.com',
                        '63523544',
                        'THERESIA KALAKA',
                        '{THERESIA_HASH}',
                        'district_admin',
                        true,
                        false,
                        false,
                        'email',
                        false,
                        now(),
                        now()
                    );
                else
                    update users
                    set
                        username = 'theresia',
                        email = 'motebang@gmail.com',
                        phone = '63523544',
                        full_name = 'THERESIA KALAKA',
                        hashed_password = '{THERESIA_HASH}',
                        role = 'district_admin',
                        is_active = true,
                        must_change_password = false,
                        updated_at = now()
                    where id = theresia_id;
                end if;

                insert into district_admin_assignments (
                    id,
                    user_id,
                    district_id,
                    is_active,
                    created_at,
                    updated_at
                )
                values (
                    '{THERESIA_ASSIGNMENT_ID}'::uuid,
                    theresia_id,
                    maseru_id,
                    true,
                    now(),
                    now()
                )
                on conflict (user_id, district_id) do update
                set
                    is_active = true,
                    updated_at = now();
            end $$;
            """
        )
    )

    op.execute(
        sa.text(
            """
            update properties
            set
                district_id = (select id from districts where slug = 'maseru' limit 1),
                area_id = case
                    when coalesce(location_area, '') ilike '%roma%'
                      or coalesce(address, '') ilike '%roma%'
                    then (select id from district_areas where slug = 'roma' limit 1)
                    else area_id
                end,
                updated_at = now()
            where district_id is null
              and (
                coalesce(location_area, '') ilike '%maseru%'
                or coalesce(location_area, '') ilike '%roma%'
                or coalesce(address, '') ilike '%maseru%'
                or coalesce(address, '') ilike '%roma%'
              )
            """
        )
    )

    op.execute(
        sa.text(
            """
            update room_listings
            set
                district_id = properties.district_id,
                area_id = coalesce(room_listings.area_id, properties.area_id),
                updated_at = now()
            from properties
            where room_listings.property_id = properties.id
              and properties.district_id is not null
              and room_listings.district_id is null
            """
        )
    )


def downgrade() -> None:
    pass
