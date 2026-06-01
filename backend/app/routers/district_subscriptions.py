from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_district_admin_district_ids, require_roles
from app.models import User, UserRole

router = APIRouter(prefix="/district", tags=["district subscriptions"])


@router.get("/subscription-status")
def district_subscription_status(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.district_admin)),
):
    district_ids = get_district_admin_district_ids(db, user)
    if not district_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No district assignment found. Contact National Admin.",
        )

    district_id = district_ids[0]
    district = db.execute(
        text("select id, name from districts where id = :district_id"),
        {"district_id": district_id},
    ).mappings().first()

    landlord_rows = db.execute(
        text(
            """
            select
                l.id as landlord_id,
                coalesce(l.business_name, u.full_name, l.email) as landlord_name,
                count(distinct p.id) as property_count,
                count(distinct case when ps.status::text = 'active' then ps.id end) as paid_property_subscriptions_count,
                count(distinct case when ps.id is null or ps.status::text <> 'active' then p.id end) as unpaid_property_subscriptions_count
            from landlords l
            join users u on u.id = l.user_id
            join properties p on p.landlord_id = l.id
            left join property_subscriptions ps on ps.property_id = p.id
            where p.district_id = :district_id
            group by l.id, l.business_name, u.full_name, l.email
            order by landlord_name asc
            """
        ),
        {"district_id": district_id},
    ).mappings().all()

    property_rows = db.execute(
        text(
            """
            select
                p.landlord_id,
                p.id as property_id,
                p.name as property_name,
                count(r.id) as room_count,
                coalesce(ps.status::text, 'past_due') as subscription_status,
                ps.renewal_date as next_due_date
            from properties p
            left join rooms r on r.property_id = p.id
            left join property_subscriptions ps on ps.property_id = p.id
            where p.district_id = :district_id
            group by p.landlord_id, p.id, p.name, ps.status, ps.renewal_date
            order by p.name asc
            """
        ),
        {"district_id": district_id},
    ).mappings().all()

    properties_by_landlord: dict[str, list[dict[str, object]]] = {}
    for row in property_rows:
        item = {
            "property_id": str(row["property_id"]),
            "property_name": row["property_name"],
            "room_count": int(row["room_count"] or 0),
            "subscription_status": row["subscription_status"],
            "last_payment_date": None,
            "next_due_date": row["next_due_date"],
        }
        properties_by_landlord.setdefault(str(row["landlord_id"]), []).append(item)

    landlords = []
    for row in landlord_rows:
        landlord_id = str(row["landlord_id"])
        unpaid = int(row["unpaid_property_subscriptions_count"] or 0)
        landlords.append(
            {
                "landlord_id": landlord_id,
                "landlord_name": row["landlord_name"],
                "property_count": int(row["property_count"] or 0),
                "paid_property_subscriptions_count": int(row["paid_property_subscriptions_count"] or 0),
                "unpaid_property_subscriptions_count": unpaid,
                "subscription_status_summary": "unpaid" if unpaid else "paid",
                "properties": properties_by_landlord.get(landlord_id, []),
            }
        )

    return {
        "district_id": str(district["id"]) if district else str(district_id),
        "district_name": district["name"] if district else "Assigned district",
        "landlords": landlords,
    }
