from app.config import settings
from app.models import PaymentMethod
from app.payment_providers.base import PaymentProvider, PaymentProviderRequest, PaymentProviderResult


class MpesaProvider(PaymentProvider):
    method = PaymentMethod.mpesa

    def initiate(self, request: PaymentProviderRequest) -> PaymentProviderResult:
        # Scaffold only: production integration should exchange credentials from
        # Render env vars and call the provider STK/push endpoint over HTTPS.
        checkout_id = f"MPESA-CHECKOUT-{request.transaction_id}"
        reference = f"MPESA-{request.idempotency_key}"
        provider_name = settings.mpesa_base_url or "MPESA sandbox"
        return PaymentProviderResult(
            checkout_request_id=checkout_id,
            provider_reference=reference,
            message=f"Payment request sent through {provider_name}. Confirm on your phone. LineLink never asks for your wallet PIN.",
        )
