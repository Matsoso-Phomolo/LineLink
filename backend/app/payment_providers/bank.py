from app.models import PaymentMethod
from app.payment_providers.base import PaymentProvider, PaymentProviderRequest, PaymentProviderResult


class BankTransferProvider(PaymentProvider):
    method = PaymentMethod.bank_transfer

    def initiate(self, request: PaymentProviderRequest) -> PaymentProviderResult:
        return PaymentProviderResult(
            checkout_request_id=None,
            provider_reference=f"BANK-{request.idempotency_key}",
            message="Use the landlord bank details and upload proof later. This payment will remain pending verification.",
        )


class CashProvider(PaymentProvider):
    method = PaymentMethod.cash

    def initiate(self, request: PaymentProviderRequest) -> PaymentProviderResult:
        return PaymentProviderResult(
            checkout_request_id=None,
            provider_reference=f"CASH-{request.idempotency_key}",
            message="Cash/manual payment recorded as pending verification for landlord or caretaker review.",
        )
