"""normalize gender and tenant categories

Revision ID: 20260602_0031
Revises: 20260601_0030
Create Date: 2026-06-02 00:31:00.000000
"""

from alembic import op


revision = "20260602_0031"
down_revision = "20260601_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        update room_listings
        set gender_preference = case
            when lower(coalesce(gender_preference, '')) in ('', 'any', 'both', 'all', 'everyone') then 'any'
            when lower(gender_preference) in ('male', 'men', 'man', 'm') then 'male'
            when lower(gender_preference) in ('female', 'women', 'woman', 'f') then 'female'
            else 'any'
        end
        where gender_preference is null
           or lower(gender_preference) not in ('any', 'male', 'female')
        """
    )
    op.execute(
        """
        update tenants
        set gender = case
            when lower(coalesce(gender, '')) in ('', 'any', 'both', 'all', 'everyone') then 'any'
            when lower(gender) in ('male', 'men', 'man', 'm') then 'male'
            when lower(gender) in ('female', 'women', 'woman', 'f') then 'female'
            else 'any'
        end
        where gender is null
           or lower(gender) not in ('any', 'male', 'female')
        """
    )
    op.execute(
        """
        update tenant_applications
        set gender = case
            when lower(coalesce(gender, '')) in ('', 'any', 'both', 'all', 'everyone') then 'any'
            when lower(gender) in ('male', 'men', 'man', 'm') then 'male'
            when lower(gender) in ('female', 'women', 'woman', 'f') then 'female'
            else 'any'
        end
        where gender is null
           or lower(gender) not in ('any', 'male', 'female')
        """
    )
    op.execute(
        """
        update tenants
        set tenant_subtype = case
            when tenant_category = 'student' and tenant_subtype in ('tertiary', 'high_school') then 'nul_student'
            when tenant_category = 'student' and tenant_subtype = 'vocational' then 'tvet_student'
            when tenant_category = 'worker' and tenant_subtype = 'contract_worker' then 'other_worker'
            when tenant_category = 'family' and tenant_subtype in ('couple', 'couple_with_children') then 'small_family'
            when tenant_category = 'family' and tenant_subtype = 'extended_family' then 'large_family'
            when tenant_category = 'other' and tenant_subtype in ('unemployed', 'retired', 'visitor', 'community_worker') then 'other'
            else tenant_subtype
        end
        where tenant_subtype is not null
        """
    )
    op.execute(
        """
        update tenant_applications
        set tenant_subtype = case
            when tenant_category = 'student' and tenant_subtype in ('tertiary', 'high_school') then 'nul_student'
            when tenant_category = 'student' and tenant_subtype = 'vocational' then 'tvet_student'
            when tenant_category = 'worker' and tenant_subtype = 'contract_worker' then 'other_worker'
            when tenant_category = 'family' and tenant_subtype in ('couple', 'couple_with_children') then 'small_family'
            when tenant_category = 'family' and tenant_subtype = 'extended_family' then 'large_family'
            when tenant_category = 'other' and tenant_subtype in ('unemployed', 'retired', 'visitor', 'community_worker') then 'other'
            else tenant_subtype
        end
        where tenant_subtype is not null
        """
    )


def downgrade() -> None:
    pass
