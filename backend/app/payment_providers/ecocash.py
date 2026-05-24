from app.config import settings
from app.models import PaymentMethod
from app.payment_providers.base import PaymentProvider, PaymentProviderRequest, PaymentProviderResult


class EcoCashProvider(PaymentProvider):
    method = PaymentMethod.ecocash

    def initiate(self, request: PaymentProviderRequest) -> PaymentProviderResult:
        checkout_id = f"ECOCASH-CHECKOUT-{request.transaction_id}"
        reference = f"ECOCASH-{request.idempotency_key}"
        provider_name = settings.ecocash_base_url or "EcoCash sandbox"
        return PaymentProviderResult(
            checkout_request_id=checkout_id,
            provider_reference=reference,
            message=f"Payment request sent through {provider_name}. Confirm on your phone. LineLink never asks for your wallet PIN.",
        )
