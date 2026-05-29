import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.audit import log_action
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import (
    AuditAction,
    Landlord,
    LandlordSubscription,
    Notification,
    Occupancy,
    PaymentMethod,
    PaymentReceipt,
    PaymentSubmission,
    PaymentSubmissionStatus,
    PaymentTransaction,
    PaymentTransactionStatus,
    RentDue,
    SubscriptionStatus,
    Tenant,
    User,
    UserRole,
)
from app.ownership import get_tenant_in_scope, scoped_query
from app.payment_providers.bank import BankTransferProvider, CashProvider
from app.payment_providers.base import PaymentProviderRequest
from app.payment_providers.ecocash import EcoCashProvider
from app.payment_providers.mpesa import MpesaProvider
from app.payment_providers.mopay import MoPayProvider
from app.rent_logic import refresh_due_status
from app.schemas import (
    PaymentCallbackPayload,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
)

router = APIRouter(prefix="/payments", tags=["payments"])


PROVIDERS = {
    PaymentMethod.mpesa: MpesaProvider(),
    PaymentMethod.ecocash: EcoCashProvider(),
    PaymentMethod.mopay_mpesa: MoPayProvider(PaymentMethod.mopay_mpesa),
    PaymentMethod.mopay_ecocash: MoPayProvider(PaymentMethod.mopay_ecocash),
    PaymentMethod.mopay_card: MoPayProvider(PaymentMethod.mopay_card),
    PaymentMethod.bank_transfer: BankTransferProvider(),
    PaymentMethod.bank: BankTransferProvider(),
    PaymentMethod.cash: CashProvider(),
}


def next_receipt_number(db: Session) -> str:
    sequence = db.query(PaymentReceipt).count() + 1

    while True:
        number = f"LL-RCPT-{sequence:06d}"

        if not db.query(PaymentReceipt).filter(
            PaymentReceipt.receipt_number == number
        ).first():
            return number

        sequence += 1


def find_transaction(
    db: Session,
    payload: PaymentCallbackPayload,
) -> PaymentTransaction | None:
    query = db.query(PaymentTransaction)

    if payload.checkout_request_id:
        item = query.filter(
            PaymentTransaction.checkout_request_id == payload.checkout_request_id
        ).first()

        if item:
            return item

    if payload.provider_reference:
        item = query.filter(
            PaymentTransaction.provider_reference == payload.provider_reference
        ).first()

        if item:
            return item

    if payload.idempotency_key:
        return query.filter(
            PaymentTransaction.idempotency_key == payload.idempotency_key
        ).first()

    return None


def find_transaction_from_dict(
    db: Session,
    payload: dict,
) -> PaymentTransaction | None:
    event_id = payload.get("webhook_event_id") or payload.get("event_id") or payload.get("id")

    if event_id:
        item = db.query(PaymentTransaction).filter(
            PaymentTransaction.webhook_event_id == str(event_id)
        ).first()

        if item:
            return item

    normalized = PaymentCallbackPayload(
        checkout_request_id=payload.get("checkout_request_id")
        or payload.get("checkoutRequestId"),
        provider_reference=payload.get("provider_reference")
        or payload.get("providerReference")
        or payload.get("reference"),
        idempotency_key=payload.get("idempotency_key")
        or payload.get("idempotencyKey"),
        status=str(
            payload.get("status")
            or payload.get("provider_status")
            or payload.get("providerStatus")
            or ""
        ),
        amount=payload.get("amount"),
        transaction_reference=payload.get("transaction_reference")
        or payload.get("transactionReference"),
        message=payload.get("message"),
        error_message=payload.get("error_message")
        or payload.get("failure_reason")
        or payload.get("failureReason"),
    )

    transaction_id = payload.get("transaction_id") or payload.get("transactionId")

    if transaction_id:
        try:
            item = db.get(PaymentTransaction, uuid.UUID(str(transaction_id)))

            if item:
                return item
        except ValueError:
            pass

    return find_transaction(db, normalized)


def complete_successful_transaction(
    db: Session,
    transaction: PaymentTransaction,
    payload: PaymentCallbackPayload,
) -> None:
    if transaction.status == PaymentTransactionStatus.successful:
        return

    transaction.status = PaymentTransactionStatus.successful
    transaction.completed_at = datetime.now(timezone.utc)
    transaction.processed_at = datetime.now(timezone.utc)
    transaction.raw_callback_json = payload.model_dump_json()
    transaction.provider_message = payload.message
    transaction.provider_status = payload.status

    if payload.provider_reference:
        transaction.provider_reference = payload.provider_reference

    if transaction.payment_type == "landlord_subscription":
        complete_successful_subscription_transaction(db, transaction, payload)
        return

    due = db.get(RentDue, transaction.rent_due_id) if transaction.rent_due_id else None

    if not transaction.tenant_id:
        return

    submission = PaymentSubmission(
        landlord_id=transaction.landlord_id,
        tenant_id=transaction.tenant_id,
        rent_due_id=transaction.rent_due_id,
        amount=payload.amount or transaction.amount,
        method=transaction.method,
        transaction_reference=payload.transaction_reference
        or transaction.provider_reference
        or transaction.idempotency_key,
        status=PaymentSubmissionStatus.approved,
        approved_at=datetime.now(timezone.utc),
    )

    db.add(submission)
    db.flush()

    transaction.payment_submission_id = submission.id

    room_id = None

    if due:
        due.amount_paid = float(due.amount_paid) + float(submission.amount)
        refresh_due_status(due)

        occupancy = db.get(Occupancy, due.occupancy_id)
        room_id = occupancy.room_id if occupancy else None

    tenant = db.get(Tenant, transaction.tenant_id)

    if tenant:
        tenant.outstanding_balance = max(
            0,
            float(tenant.outstanding_balance or 0) - float(submission.amount),
        )

        if tenant.user_id:
            db.add(
                Notification(
                    user_id=tenant.user_id,
                    title="Payment successful",
                    body=f"Payment {submission.transaction_reference} was confirmed and receipted.",
                    category="payments",
                )
            )

    receipt = PaymentReceipt(
        landlord_id=transaction.landlord_id,
        tenant_id=transaction.tenant_id,
        room_id=room_id,
        payment_submission_id=submission.id,
        receipt_number=next_receipt_number(db),
        amount=submission.amount,
        method=submission.method,
        transaction_reference=submission.transaction_reference,
        pdf_url=f"/payment-submissions/{submission.id}/receipt",
    )

    db.add(receipt)


def complete_successful_subscription_transaction(
    db: Session,
    transaction: PaymentTransaction,
    payload: PaymentCallbackPayload,
) -> None:
    subscription = (
        db.get(LandlordSubscription, transaction.subscription_id)
        if transaction.subscription_id
        else None
    )

    landlord = db.get(Landlord, transaction.landlord_id)

    if not subscription or not landlord:
        transaction.failure_reason = (
            "Subscription or landlord was not found for successful payment"
        )
        return

    today = datetime.now(timezone.utc).date()

    subscription.status = SubscriptionStatus.active

    if subscription.renewal_date and subscription.renewal_date > today:
        month = subscription.renewal_date.month + 1
        year = subscription.renewal_date.year + (1 if month > 12 else 0)
        month = 1 if month > 12 else month
        subscription.renewal_date = subscription.renewal_date.replace(
            year=year,
            month=month,
        )
    else:
        month = today.month + 1
        year = today.year + (1 if month > 12 else 0)
        month = 1 if month > 12 else month
        subscription.renewal_date = today.replace(year=year, month=month)

    if landlord.user_id:
        db.add(
            Notification(
                user_id=landlord.user_id,
                title="Subscription payment successful",
                body="Your LineLink landlord subscription payment was confirmed.",
                category="subscriptions",
            )
        )

    receipt = PaymentReceipt(
        landlord_id=transaction.landlord_id,
        tenant_id=None,
        room_id=None,
        payment_submission_id=None,
        subscription_id=subscription.id,
        receipt_type="landlord_subscription",
        receipt_number=next_receipt_number(db),
        amount=payload.amount or transaction.amount,
        method=transaction.method,
        transaction_reference=payload.transaction_reference
        or transaction.provider_reference
        or transaction.idempotency_key,
        pdf_url=f"/payments/transactions/{transaction.id}/receipt",
    )

    db.add(receipt)


@router.post("/initiate", response_model=PaymentInitiateResponse)
def initiate_payment(
    payload: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not payload.rent_due_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rent_due_id is required for tenant rent payments",
        )

    due = db.get(RentDue, payload.rent_due_id)

    if not due:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rent due not found",
        )

    tenant_id = payload.tenant_id or due.tenant_id
    tenant = get_tenant_in_scope(db, user, tenant_id)

    if due.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rent due does not belong to tenant",
        )

    if payload.method not in PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported payment method",
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
        or f"{tenant.id}-{payload.rent_due_id}-{payload.method.value}-{payload.amount}"
    )

    existing = db.query(PaymentTransaction).filter(
        PaymentTransaction.idempotency_key == idempotency_key
    ).first()

    if existing:
        return existing

    transaction = PaymentTransaction(
        landlord_id=tenant.landlord_id,
        tenant_id=tenant.id,
        rent_due_id=due.id,
        amount=payload.amount,
        method=payload.method,
        payer_phone=payload.payer_phone,
        idempotency_key=idempotency_key,
        status=PaymentTransactionStatus.pending_verification
        if payload.method
        in {
            PaymentMethod.bank,
            PaymentMethod.bank_transfer,
            PaymentMethod.cash,
        }
        else PaymentTransactionStatus.pending,
    )

    db.add(transaction)
    db.flush()

    result = PROVIDERS[payload.method].initiate(
        PaymentProviderRequest(
            transaction.id,
            float(payload.amount),
            payload.payer_phone,
            idempotency_key,
        )
    )

    transaction.checkout_request_id = result.checkout_request_id
    transaction.provider_reference = result.provider_reference
    transaction.provider_message = result.message

    log_action(
        db,
        AuditAction.create_payment,
        user,
        tenant.landlord_id,
        "PaymentTransaction",
        transaction.id,
    )

    db.commit()
    db.refresh(transaction)

    return transaction


@router.get("/transactions", response_model=list[PaymentInitiateResponse])
def list_transactions(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    return (
        scoped_query(db, user, PaymentTransaction)
        .order_by(PaymentTransaction.created_at.desc())
        .all()
    )


@router.get("/transactions/{transaction_id}", response_model=PaymentInitiateResponse)
def get_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
            UserRole.tenant,
        )
    ),
):
    transaction = db.get(PaymentTransaction, transaction_id)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment transaction not found",
        )

    if user.role == UserRole.tenant:
        tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()

        if not tenant or transaction.tenant_id != tenant.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Payment transaction is outside your account",
            )
    else:
        if not (
            scoped_query(db, user, PaymentTransaction)
            .filter(PaymentTransaction.id == transaction.id)
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Payment transaction is outside your scope",
            )

    return transaction


@router.get("/receipts")
def list_receipts(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
            UserRole.tenant,
        )
    ),
):
    query = db.query(PaymentReceipt)

    if user.role == UserRole.tenant:
        tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()

        if not tenant:
            return []

        query = query.filter(PaymentReceipt.tenant_id == tenant.id)

    elif user.role != UserRole.admin:
        query = scoped_query(db, user, PaymentReceipt)

    return query.order_by(PaymentReceipt.issued_at.desc()).limit(100).all()


@router.get("/gateway-health")
def gateway_health(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    last = (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.webhook_event_id.is_not(None))
        .order_by(
            PaymentTransaction.processed_at.desc().nullslast(),
            PaymentTransaction.updated_at.desc(),
        )
        .first()
    )

    return {
        "mopay_environment": settings.mopay_environment,
        "webhook_url": settings.mopay_callback_url
        or f"{settings.public_base_url}/payments/callback/mopay",
        "callback_url": settings.mopay_callback_url,
        "return_url": settings.mopay_return_url,
        "configured": {
            "MOPAY_BASE_URL": bool(settings.mopay_base_url),
            "MOPAY_API_KEY": bool(settings.mopay_api_key),
            "MOPAY_MERCHANT_ID": bool(settings.mopay_merchant_id),
            "MOPAY_WEBHOOK_SECRET": bool(settings.mopay_webhook_secret),
            "MOPAY_CALLBACK_URL": bool(settings.mopay_callback_url),
            "MOPAY_RETURN_URL": bool(settings.mopay_return_url),
        },
        "last_webhook_received": last.processed_at if last else None,
        "failed_webhook_count": db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.payment_type.in_(["rent", "landlord_subscription"]),
            PaymentTransaction.status == PaymentTransactionStatus.failed,
        )
        .count(),
        "successful_payment_count": db.query(PaymentTransaction)
        .filter(PaymentTransaction.status == PaymentTransactionStatus.successful)
        .count(),
    }


@router.post("/callback/mpesa")
def mpesa_callback(
    payload: PaymentCallbackPayload,
    db: Session = Depends(get_db),
):
    return handle_callback(db, payload, PaymentMethod.mpesa)


@router.post("/callback/ecocash")
def ecocash_callback(
    payload: PaymentCallbackPayload,
    db: Session = Depends(get_db),
):
    return handle_callback(db, payload, PaymentMethod.ecocash)


@router.post("/callback/mopay")
async def mopay_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    raw_body = await request.body()

    signature = request.headers.get("x-mopay-signature") or request.headers.get(
        "x-signature"
    )

    verified = verify_mopay_signature(raw_body, signature)

    if settings.mopay_webhook_secret and not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MoPay webhook signature",
        )

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        )

    transaction = find_transaction_from_dict(db, payload)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment transaction not found",
        )

    event_id = payload.get("webhook_event_id") or payload.get("event_id") or payload.get("id")

    if event_id and transaction.webhook_event_id == str(event_id) and transaction.processed_at:
        return {
            "detail": "duplicate webhook ignored",
            "transaction_id": str(transaction.id),
            "status": transaction.status.value,
        }

    callback = PaymentCallbackPayload(
        checkout_request_id=payload.get("checkout_request_id")
        or payload.get("checkoutRequestId")
        or transaction.checkout_request_id,
        provider_reference=payload.get("provider_reference")
        or payload.get("providerReference")
        or payload.get("reference")
        or transaction.provider_reference,
        idempotency_key=payload.get("idempotency_key")
        or payload.get("idempotencyKey")
        or transaction.idempotency_key,
        status=str(
            payload.get("status")
            or payload.get("provider_status")
            or payload.get("providerStatus")
            or ""
        ),
        amount=payload.get("amount") or float(transaction.amount),
        transaction_reference=payload.get("transaction_reference")
        or payload.get("transactionReference")
        or payload.get("receipt_number"),
        message=payload.get("message"),
        error_message=payload.get("error_message")
        or payload.get("failure_reason")
        or payload.get("failureReason"),
    )

    transaction.webhook_event_id = str(event_id) if event_id else transaction.webhook_event_id
    transaction.verified_signature = verified
    transaction.raw_callback_json = json.dumps(payload)
    transaction.provider_status = callback.status

    normalized_status = callback.status.lower()

    if normalized_status in {"success", "successful", "paid", "completed"}:
        complete_successful_transaction(db, transaction, callback)
    else:
        transaction.status = PaymentTransactionStatus.failed
        transaction.provider_error = (
            callback.error_message
            or callback.message
            or "MoPay reported payment failure"
        )
        transaction.failure_reason = transaction.provider_error
        transaction.processed_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "detail": "callback processed",
        "transaction_id": str(transaction.id),
        "status": transaction.status.value,
    }


def verify_mopay_signature(
    raw_body: bytes,
    signature: str | None,
) -> bool:
    if not settings.mopay_webhook_secret:
        return False

    if not signature:
        return False

    expected = hmac.new(
        settings.mopay_webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    provided = signature.removeprefix("sha256=").strip()

    return hmac.compare_digest(expected, provided)


def handle_callback(
    db: Session,
    payload: PaymentCallbackPayload,
    method: PaymentMethod,
):
    transaction = find_transaction(db, payload)

    if not transaction or transaction.method != method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment transaction not found",
        )

    normalized_status = payload.status.lower()

    if normalized_status in {"success", "successful", "paid", "completed"}:
        complete_successful_transaction(db, transaction, payload)
    else:
        transaction.status = PaymentTransactionStatus.failed
        transaction.provider_error = (
            payload.error_message
            or payload.message
            or "Provider reported payment failure"
        )
        transaction.failure_reason = transaction.provider_error
        transaction.provider_status = payload.status
        transaction.processed_at = datetime.now(timezone.utc)
        transaction.raw_callback_json = json.dumps(payload.model_dump(mode="json"))

    db.commit()

    return {
        "detail": "callback processed",
        "transaction_id": str(transaction.id),
        "status": transaction.status.value,
    }
