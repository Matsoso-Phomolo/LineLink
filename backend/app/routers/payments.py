import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit import log_action
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import (
    AuditAction,
    Notification,
    Occupancy,
    PaymentMethod,
    PaymentReceipt,
    PaymentSubmission,
    PaymentSubmissionStatus,
    PaymentTransaction,
    PaymentTransactionStatus,
    RentDue,
    Tenant,
    User,
    UserRole,
)
from app.ownership import get_tenant_in_scope, landlord_scope_filter
from app.payment_providers.bank import BankTransferProvider, CashProvider
from app.payment_providers.base import PaymentProviderRequest
from app.payment_providers.ecocash import EcoCashProvider
from app.payment_providers.mpesa import MpesaProvider
from app.rent_logic import refresh_due_status
from app.schemas import PaymentCallbackPayload, PaymentInitiateRequest, PaymentInitiateResponse

router = APIRouter(prefix="/payments", tags=["payments"])


PROVIDERS = {
    PaymentMethod.mpesa: MpesaProvider(),
    PaymentMethod.ecocash: EcoCashProvider(),
    PaymentMethod.bank_transfer: BankTransferProvider(),
    PaymentMethod.bank: BankTransferProvider(),
    PaymentMethod.cash: CashProvider(),
}


def next_receipt_number(db: Session) -> str:
    sequence = db.query(PaymentReceipt).count() + 1
    while True:
        number = f"LL-RCPT-{sequence:06d}"
        if not db.query(PaymentReceipt).filter(PaymentReceipt.receipt_number == number).first():
            return number
        sequence += 1


def find_transaction(db: Session, payload: PaymentCallbackPayload) -> PaymentTransaction | None:
    query = db.query(PaymentTransaction)
    if payload.checkout_request_id:
        item = query.filter(PaymentTransaction.checkout_request_id == payload.checkout_request_id).first()
        if item:
            return item
    if payload.provider_reference:
        item = query.filter(PaymentTransaction.provider_reference == payload.provider_reference).first()
        if item:
            return item
    if payload.idempotency_key:
        return query.filter(PaymentTransaction.idempotency_key == payload.idempotency_key).first()
    return None


def complete_successful_transaction(db: Session, transaction: PaymentTransaction, payload: PaymentCallbackPayload) -> None:
    if transaction.status == PaymentTransactionStatus.successful:
        return
    transaction.status = PaymentTransactionStatus.successful
    transaction.completed_at = datetime.now(timezone.utc)
    transaction.raw_callback_json = payload.model_dump_json()
    transaction.provider_message = payload.message
    if payload.provider_reference:
        transaction.provider_reference = payload.provider_reference

    due = db.get(RentDue, transaction.rent_due_id) if transaction.rent_due_id else None
    submission = PaymentSubmission(
        landlord_id=transaction.landlord_id,
        tenant_id=transaction.tenant_id,
        rent_due_id=transaction.rent_due_id,
        amount=payload.amount or transaction.amount,
        method=transaction.method,
        transaction_reference=payload.transaction_reference or transaction.provider_reference or transaction.idempotency_key,
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
        tenant.outstanding_balance = max(0, float(tenant.outstanding_balance or 0) - float(submission.amount))
        if tenant.user_id:
            db.add(Notification(user_id=tenant.user_id, title="Payment successful", body=f"Payment {submission.transaction_reference} was confirmed and receipted.", category="payments"))
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


@router.post("/initiate", response_model=PaymentInitiateResponse)
def initiate_payment(payload: PaymentInitiateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    due = db.get(RentDue, payload.rent_due_id)
    if not due:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rent due not found")
    tenant_id = payload.tenant_id or due.tenant_id
    tenant = get_tenant_in_scope(db, user, tenant_id)
    if due.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rent due does not belong to tenant")
    if payload.method not in PROVIDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported payment method")
    idempotency_key = payload.idempotency_key or f"{tenant.id}-{payload.rent_due_id}-{payload.method.value}-{payload.amount}"
    existing = db.query(PaymentTransaction).filter(PaymentTransaction.idempotency_key == idempotency_key).first()
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
        status=PaymentTransactionStatus.pending_verification if payload.method in {PaymentMethod.bank, PaymentMethod.bank_transfer, PaymentMethod.cash} else PaymentTransactionStatus.pending,
    )
    db.add(transaction)
    db.flush()
    result = PROVIDERS[payload.method].initiate(PaymentProviderRequest(transaction.id, float(payload.amount), payload.payer_phone, idempotency_key))
    transaction.checkout_request_id = result.checkout_request_id
    transaction.provider_reference = result.provider_reference
    transaction.provider_message = result.message
    log_action(db, AuditAction.create_payment, user, tenant.landlord_id, "PaymentTransaction", transaction.id)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/transactions", response_model=list[PaymentInitiateResponse])
def list_transactions(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    return landlord_scope_filter(db, user, PaymentTransaction).order_by(PaymentTransaction.created_at.desc()).all()


@router.post("/callback/mpesa")
def mpesa_callback(payload: PaymentCallbackPayload, db: Session = Depends(get_db)):
    return handle_callback(db, payload, PaymentMethod.mpesa)


@router.post("/callback/ecocash")
def ecocash_callback(payload: PaymentCallbackPayload, db: Session = Depends(get_db)):
    return handle_callback(db, payload, PaymentMethod.ecocash)


def handle_callback(db: Session, payload: PaymentCallbackPayload, method: PaymentMethod):
    transaction = find_transaction(db, payload)
    if not transaction or transaction.method != method:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment transaction not found")
    normalized_status = payload.status.lower()
    if normalized_status in {"success", "successful", "paid", "completed"}:
        complete_successful_transaction(db, transaction, payload)
    else:
        transaction.status = PaymentTransactionStatus.failed
        transaction.provider_error = payload.error_message or payload.message or "Provider reported payment failure"
        transaction.raw_callback_json = json.dumps(payload.model_dump(mode="json"))
    db.commit()
    return {"detail": "callback processed", "transaction_id": str(transaction.id), "status": transaction.status.value}
