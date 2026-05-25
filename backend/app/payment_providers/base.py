from dataclasses import dataclass
from uuid import UUID

from app.models import PaymentMethod


@dataclass
class PaymentProviderRequest:
    transaction_id: UUID
    amount: float
    payer_phone: str | None
    idempotency_key: str
    currency: str = "LSL"
    description: str | None = None
    method_variant: str | None = None


@dataclass
class PaymentProviderResult:
    checkout_request_id: str | None
    provider_reference: str | None
    message: str


class PaymentProvider:
    method: PaymentMethod

    def initiate(self, request: PaymentProviderRequest) -> PaymentProviderResult:
        raise NotImplementedError
