from datetime import date
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import (
    get_actor_landlord_id,
    get_current_user,
    get_district_admin_district_ids,
    require_roles,
)
from app.models import (
    LandlordSubscription,
    PaymentMethod,
    PaymentTransaction,
    PaymentTransactionStatus,
    DistrictAdminSubscriptionPermission,
    SubscriptionPlan,
    SubscriptionPricingRule,
    SubscriptionStatus,
    User,
    UserRole,
)
from app.ownership import scoped_query
from app.payment_providers.base import PaymentProviderRequest
from app.routers.payments import PROVIDERS
from app.schemas import (
    LandlordSubscriptionCreate,
    LandlordSubscriptionRead,
    PaymentInitiateResponse,
    SubscriptionPayRequest,
    SubscriptionPlanCreate,
    SubscriptionPlanRead,
    SubscriptionPricingRuleRead,
    SubscriptionPricingRuleUpsert,
    DistrictSubscriptionPermissionUpdate,
)
from app.subscription_rules import default_subscription_rules

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def assert_subscription_pricing_permission(
    db: Session,
    user: User,
    district_id: uuid.UUID | None,
) -> None:
    if user.role == UserRole.national_admin:
        return

    if user.role != UserRole.district_admin or not district_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only National Admin can manage national subscription pricing.",
        )

    district_ids = set(get_district_admin_district_ids(db, user))
    if district_id not in district_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="District Admin can only manage pricing in their assigned district.",
        )

    permission = (
        db.query(DistrictAdminSubscriptionPermission)
        .filter(
            DistrictAdminSubscriptionPermission.district_admin_user_id == user.id,
            DistrictAdminSubscriptionPermission.district_id == district_id,
            DistrictAdminSubscriptionPermission.can_manage_subscriptions.is_(True),
        )
        .first()
    )

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription pricing is locked by National Admin for this district.",
        )


@router.get("/pricing-rules", response_model=list[SubscriptionPricingRuleRead])
def list_pricing_rules(
    district_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin, UserRole.district_admin)),
):
    query = db.query(SubscriptionPricingRule)

    if user.role == UserRole.district_admin:
        district_ids = set(get_district_admin_district_ids(db, user))
        if district_id:
            if district_id not in district_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="District is outside your assigned scope.",
                )
            query = query.filter(SubscriptionPricingRule.district_id == district_id)
        else:
            query = query.filter(SubscriptionPricingRule.district_id.in_(district_ids))
    elif district_id:
        query = query.filter(SubscriptionPricingRule.district_id == district_id)

    return query.order_by(SubscriptionPricingRule.district_id.nullsfirst(), SubscriptionPricingRule.min_rooms.asc()).all()


@router.post("/pricing-rules", response_model=SubscriptionPricingRuleRead)
def upsert_pricing_rule(
    payload: SubscriptionPricingRuleUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin, UserRole.district_admin)),
):
    assert_subscription_pricing_permission(db, user, payload.district_id)

    rule = (
        db.query(SubscriptionPricingRule)
        .filter(
            SubscriptionPricingRule.district_id == payload.district_id,
            SubscriptionPricingRule.tier_name == payload.tier_name,
        )
        .first()
    )

    if not rule:
        rule = SubscriptionPricingRule(
            district_id=payload.district_id,
            tier_name=payload.tier_name,
            created_by_user_id=user.id,
        )
        db.add(rule)

    rule.min_rooms = payload.min_rooms
    rule.max_rooms = payload.max_rooms
    rule.monthly_amount = payload.monthly_amount
    rule.is_active = payload.is_active
    rule.updated_by_user_id = user.id

    db.commit()
    db.refresh(rule)
    return rule


@router.get("/pricing-defaults")
def get_pricing_defaults():
    return default_subscription_rules()


@router.post("/district-permissions")
def set_district_subscription_permission(
    payload: DistrictSubscriptionPermissionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin)),
):
    district_admin = db.get(User, payload.district_admin_user_id)
    if not district_admin or district_admin.role != UserRole.district_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District Admin user not found.",
        )

    district_ids = set(get_district_admin_district_ids(db, district_admin))
    if not district_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District Admin assignment not found.",
        )

    permission_records = []
    for district_id in district_ids:
        permission = (
            db.query(DistrictAdminSubscriptionPermission)
            .filter(
                DistrictAdminSubscriptionPermission.district_admin_user_id == payload.district_admin_user_id,
                DistrictAdminSubscriptionPermission.district_id == district_id,
            )
            .first()
        )
        if not permission:
            permission = DistrictAdminSubscriptionPermission(
                district_admin_user_id=payload.district_admin_user_id,
                district_id=district_id,
                granted_by_user_id=user.id,
            )
            db.add(permission)

        permission.can_manage_subscriptions = payload.can_manage_subscriptions
        permission.granted_by_user_id = user.id
        permission_records.append(permission)

    db.commit()
    return {
        "district_admin_user_id": str(payload.district_admin_user_id),
        "can_manage_subscriptions": payload.can_manage_subscriptions,
        "districts_updated": len(permission_records),
    }


@router.get("/district-permissions")
def list_district_subscription_permissions(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin, UserRole.district_admin)),
):
    return [
        {
            "id": str(item.id),
            "district_admin_user_id": str(item.district_admin_user_id),
            "district_id": str(item.district_id),
            "can_manage_subscriptions": item.can_manage_subscriptions,
        }
        for item in db.query(DistrictAdminSubscriptionPermission).all()
    ]


def subscription_in_scope(
    db: Session,
    user: User,
    subscription_id: uuid.UUID,
) -> LandlordSubscription:
    subscription = (
        scoped_query(db, user, LandlordSubscription)
        .filter(LandlordSubscription.id == subscription_id)
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    return subscription


@router.post("/plans", response_model=SubscriptionPlanRead)
def create_plan(
    payload: SubscriptionPlanCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    plan = SubscriptionPlan(**payload.model_dump())

    db.add(plan)
    db.commit()
    db.refresh(plan)

    return plan


@router.get("/plans", response_model=list[SubscriptionPlanRead])
def list_plans(
    db: Session = Depends(get_db),
    _: User = Depends(
        require_roles(
            UserRole.national_admin,
            UserRole.landlord,
            UserRole.caretaker,
            UserRole.district_admin,
        )
    ),
):
    return (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.monthly_price.asc())
        .all()
    )


@router.put("/plans/{plan_id}", response_model=SubscriptionPlanRead)
def update_plan(
    plan_id: uuid.UUID,
    payload: SubscriptionPlanCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    plan = db.get(SubscriptionPlan, plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found",
        )

    for key, value in payload.model_dump().items():
        setattr(plan, key, value)

    db.commit()
    db.refresh(plan)

    return plan


@router.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    plan = db.get(SubscriptionPlan, plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found",
        )

    plan.is_active = False

    db.commit()

    return {"detail": "Subscription plan disabled"}


@router.post("", response_model=LandlordSubscriptionRead)
def assign_subscription(
    payload: LandlordSubscriptionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.national_admin)),
):
    subscription = LandlordSubscription(**payload.model_dump())

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return subscription


@router.get("", response_model=list[LandlordSubscriptionRead])
def list_subscriptions(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.national_admin,
            UserRole.district_admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    return (
        scoped_query(db, user, LandlordSubscription)
        .order_by(LandlordSubscription.created_at.desc())
        .all()
    )


@router.get("/mine", response_model=list[LandlordSubscriptionRead])
def my_subscriptions(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.landlord,
            UserRole.national_admin,
        )
    ),
):
    if user.role == UserRole.national_admin:
        return (
            db.query(LandlordSubscription)
            .order_by(LandlordSubscription.created_at.desc())
            .all()
        )

    landlord_id = get_actor_landlord_id(db, user)

    return (
        db.query(LandlordSubscription)
        .filter(LandlordSubscription.landlord_id == landlord_id)
        .order_by(LandlordSubscription.created_at.desc())
        .all()
    )


@router.post("/pay", response_model=PaymentInitiateResponse)
def pay_subscription(
    payload: SubscriptionPayRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.landlord,
            UserRole.national_admin,
        )
    ),
):
    landlord_id = get_actor_landlord_id(db, user)

    if user.role != UserRole.national_admin and not landlord_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No landlord scope available",
        )

    subscription = (
        db.get(LandlordSubscription, payload.subscription_id)
        if payload.subscription_id
        else None
    )

    if subscription and user.role != UserRole.national_admin:
        scoped_subscription = (
            scoped_query(db, user, LandlordSubscription)
            .filter(LandlordSubscription.id == subscription.id)
            .first()
        )

        if not scoped_subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscription is outside your scope",
            )

    if not subscription:
        if not payload.plan_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="subscription_id or plan_id is required",
            )

        plan = db.get(SubscriptionPlan, payload.plan_id)

        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription plan not found",
            )

        target_landlord_id = (
            landlord_id
            if user.role != UserRole.national_admin
            else None
        )

        if not target_landlord_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Admin must assign subscriptions "
                    "before paying on behalf of landlord"
                ),
            )

        subscription = LandlordSubscription(
            landlord_id=target_landlord_id,
            plan_id=plan.id,
            status=SubscriptionStatus.past_due,
            start_date=date.today(),
            renewal_date=date.today(),
        )

        db.add(subscription)
        db.flush()

    if (
        user.role != UserRole.national_admin
        and subscription.landlord_id != landlord_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription is outside your landlord account",
        )

    if (
        payload.method not in PROVIDERS
        or payload.method == PaymentMethod.cash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported subscription payment method",
        )

    if (
        payload.method
        in {
            PaymentMethod.mpesa,
            PaymentMethod.ecocash,
            PaymentMethod.mopay_mpesa,
            PaymentMethod.mopay_ecocash,
        }
        and not payload.payer_phone
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required for mobile money payments",
        )

    idempotency_key = (
        payload.idempotency_key
        or (
            f"subscription-{subscription.id}-"
            f"{payload.method.value}-{payload.amount}"
        )
    )

    existing = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.idempotency_key
            == idempotency_key
        )
        .first()
    )

    if existing:
        return existing

    transaction = PaymentTransaction(
        landlord_id=subscription.landlord_id,
        tenant_id=None,
        subscription_id=subscription.id,
        payment_type="landlord_subscription",
        amount=payload.amount,
        method=payload.method,
        payer_phone=payload.payer_phone,
        idempotency_key=idempotency_key,
        status=(
            PaymentTransactionStatus.pending_verification
            if payload.method
            in {
                PaymentMethod.bank,
                PaymentMethod.bank_transfer,
            }
            else PaymentTransactionStatus.pending
        ),
    )

    db.add(transaction)
    db.flush()

    result = PROVIDERS[payload.method].initiate(
        PaymentProviderRequest(
            transaction.id,
            float(payload.amount),
            payload.payer_phone,
            idempotency_key,
            description="Rentalink landlord subscription",
            method_variant=payload.method.value,
        )
    )

    transaction.checkout_request_id = result.checkout_request_id
    transaction.provider_reference = result.provider_reference
    transaction.provider_message = result.message

    db.commit()
    db.refresh(transaction)

    return transaction
