import uuid

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_actor_landlord_id, require_roles
from app.models import PaymentMethod, PaymentTransaction, PaymentTransactionStatus, LandlordSubscription, SubscriptionPlan, SubscriptionStatus, User, UserRole
from app.payment_providers.base import PaymentProviderRequest
from app.routers.payments import PROVIDERS
from app.schemas import LandlordSubscriptionCreate, LandlordSubscriptionRead, PaymentInitiateResponse, SubscriptionPayRequest, SubscriptionPlanCreate, SubscriptionPlanRead

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/plans", response_model=SubscriptionPlanRead)
def create_plan(payload: SubscriptionPlanCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    plan = SubscriptionPlan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/plans", response_model=list[SubscriptionPlanRead])
def list_plans(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    return db.query(SubscriptionPlan).order_by(SubscriptionPlan.monthly_price.asc()).all()


@router.put("/plans/{plan_id}", response_model=SubscriptionPlanRead)
def update_plan(plan_id: uuid.UUID, payload: SubscriptionPlanCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    plan = db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found")
    for key, value in payload.model_dump().items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    plan = db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found")
    plan.is_active = False
    db.commit()
    return {"detail": "Subscription plan disabled"}


@router.post("", response_model=LandlordSubscriptionRead)
def assign_subscription(payload: LandlordSubscriptionCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    subscription = LandlordSubscription(**payload.model_dump())
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.get("", response_model=list[LandlordSubscriptionRead])
def list_subscriptions(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    return db.query(LandlordSubscription).order_by(LandlordSubscription.created_at.desc()).all()


@router.get("/mine", response_model=list[LandlordSubscriptionRead])
def my_subscriptions(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.landlord, UserRole.admin))):
    if user.role == UserRole.admin:
        return db.query(LandlordSubscription).order_by(LandlordSubscription.created_at.desc()).all()
    landlord_id = get_actor_landlord_id(db, user)
    return db.query(LandlordSubscription).filter(LandlordSubscription.landlord_id == landlord_id).order_by(LandlordSubscription.created_at.desc()).all()


@router.post("/pay", response_model=PaymentInitiateResponse)
def pay_subscription(payload: SubscriptionPayRequest, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.landlord, UserRole.admin))):
    landlord_id = get_actor_landlord_id(db, user)
    if user.role != UserRole.admin and not landlord_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No landlord scope available")
    subscription = db.get(LandlordSubscription, payload.subscription_id) if payload.subscription_id else None
    if not subscription:
        if not payload.plan_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="subscription_id or plan_id is required")
        plan = db.get(SubscriptionPlan, payload.plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found")
        target_landlord_id = landlord_id if user.role != UserRole.admin else None
        if not target_landlord_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin must assign subscriptions before paying on behalf of landlord")
        subscription = LandlordSubscription(
            landlord_id=target_landlord_id,
            plan_id=plan.id,
            status=SubscriptionStatus.past_due,
            start_date=date.today(),
            renewal_date=date.today(),
        )
        db.add(subscription)
        db.flush()
    if user.role != UserRole.admin and subscription.landlord_id != landlord_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subscription is outside your landlord account")
    if payload.method not in PROVIDERS or payload.method == PaymentMethod.cash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported subscription payment method")
    if payload.method in {PaymentMethod.mpesa, PaymentMethod.ecocash, PaymentMethod.mopay_mpesa, PaymentMethod.mopay_ecocash} and not payload.payer_phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number is required for mobile money payments")
    idempotency_key = payload.idempotency_key or f"subscription-{subscription.id}-{payload.method.value}-{payload.amount}"
    existing = db.query(PaymentTransaction).filter(PaymentTransaction.idempotency_key == idempotency_key).first()
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
        status=PaymentTransactionStatus.pending_verification if payload.method in {PaymentMethod.bank, PaymentMethod.bank_transfer} else PaymentTransactionStatus.pending,
    )
    db.add(transaction)
    db.flush()
    result = PROVIDERS[payload.method].initiate(PaymentProviderRequest(transaction.id, float(payload.amount), payload.payer_phone, idempotency_key, description="LineLink landlord subscription", method_variant=payload.method.value))
    transaction.checkout_request_id = result.checkout_request_id
    transaction.provider_reference = result.provider_reference
    transaction.provider_message = result.message
    db.commit()
    db.refresh(transaction)
    return transaction
