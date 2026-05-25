from app.config import settings
from app.models import PaymentMethod
from app.payment_providers.base import PaymentProvider, PaymentProviderRequest, PaymentProviderResult


class MoPayProvider(PaymentProvider):
    def __init__(self, method: PaymentMethod):
        self.method = method

    def initiate(self, request: PaymentProviderRequest) -> PaymentProviderResult:
        variant = {
            PaymentMethod.mopay_mpesa: "M-Pesa",
            PaymentMethod.mopay_ecocash: "EcoCash",
            PaymentMethod.mopay_card: "Card",
        }.get(self.method, "MoPay")
        checkout_id = f"MOPAY-{variant.upper().replace('-', '').replace(' ', '')}-{request.transaction_id}"
        reference = f"MOPAY-{request.idempotency_key}"
        environment = settings.mopay_environment or "sandbox"
        provider_name = settings.mopay_base_url or f"MoPay {environment}"
        phone_note = " Confirm externally on your phone." if self.method in {PaymentMethod.mopay_mpesa, PaymentMethod.mopay_ecocash} else " Complete card checkout externally."
        return PaymentProviderResult(
            checkout_request_id=checkout_id,
            provider_reference=reference,
            message=f"{variant} payment request created through {provider_name}.{phone_note} LineLink never asks for wallet PINs or card secrets.",
        )
