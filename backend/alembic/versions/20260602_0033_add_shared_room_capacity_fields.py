"""add shared room capacity fields

Revision ID: 20260602_0033
Revises: 20260602_0032
Create Date: 2026-06-02 00:33:00.000000
"""

from alembic import op


revision = "20260602_0033"
down_revision = "20260602_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        begin
            if not exists (select 1 from pg_type where typname = 'occupancy_mode') then
                create type occupancy_mode as enum ('private', 'shared_independent');
            end if;
        end $$;
        """
    )
    op.execute("alter table rooms add column if not exists occupancy_mode occupancy_mode not null default 'private'")
    op.execute("alter table rooms add column if not exists max_occupants integer not null default 1")
    op.execute(
        """
        update rooms
        set
            occupancy_mode = case
                when coalesce(max_people, occupancy_limit, 1) > 1 then 'shared_independent'::occupancy_mode
                else 'private'::occupancy_mode
            end,
            max_occupants = greatest(coalesce(max_people, occupancy_limit, 1), 1)
        """
    )
    op.execute("update rooms set max_occupants = 1 where occupancy_mode = 'private'")
    op.execute("alter table occupancies add column if not exists is_active boolean not null default true")
    op.execute("alter table occupancies add column if not exists assigned_at timestamp with time zone")
    op.execute("alter table occupancies add column if not exists ended_at timestamp with time zone")
    op.execute(
        """
        update occupancies
        set
            is_active = case when status::text = 'active' then true else false end,
            assigned_at = coalesce(assigned_at, created_at),
            ended_at = case when status::text = 'active' then ended_at else coalesce(ended_at, updated_at) end
        """
    )
    op.execute("create index if not exists ix_rooms_occupancy_mode on rooms (occupancy_mode)")
    op.execute("create index if not exists ix_rooms_max_occupants on rooms (max_occupants)")
    op.execute("create index if not exists ix_occupancies_is_active on occupancies (is_active)")
    op.execute("create index if not exists ix_occupancies_assigned_at on occupancies (assigned_at)")
    op.execute("create index if not exists ix_occupancies_ended_at on occupancies (ended_at)")
    op.execute(
        """
        with active_slots as (
            select
                id,
                row_number() over (
                    partition by room_id
                    order by coalesce(assigned_at, created_at), id
                ) as slot_number
            from occupancies
            where is_active is true
              and status::text = 'active'
        )
        update occupancies o
        set occupancy_slot_number = active_slots.slot_number
        from active_slots
        where o.id = active_slots.id
        """
    )
    op.execute(
        """
        create unique index if not exists uq_active_room_occupancy_slot
        on occupancies (room_id, occupancy_slot_number)
        where is_active is true and status = 'active'::occupancy_status
        """
    )


def downgrade() -> None:
    pass
