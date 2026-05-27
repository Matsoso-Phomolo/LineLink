import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    landlord = "landlord"
    caretaker = "caretaker"
    tenant = "tenant"


class RoomStatus(str, enum.Enum):
    vacant = "vacant"
    occupied = "occupied"
    maintenance = "maintenance"


class RoomType(str, enum.Enum):
    single = "single"
    double = "double"


class TenantType(str, enum.Enum):
    student = "student"
    non_student = "non_student"


class TenantVerificationStatus(str, enum.Enum):
    pending_verification = "pending_verification"
    verified = "verified"
    rejected_verification = "rejected_verification"


class TenantStatus(str, enum.Enum):
    active = "active"
    overdue = "overdue"
    moved_out = "moved_out"
    disabled = "disabled"


class OccupancyStatus(str, enum.Enum):
    active = "active"
    ended = "ended"
    transferred = "transferred"


class RentDueStatus(str, enum.Enum):
    unpaid = "unpaid"
    partial = "partial"
    paid = "paid"
    overdue = "overdue"


class PaymentMethod(str, enum.Enum):
    mpesa = "mpesa"
    ecocash = "ecocash"
    orange_money = "orange_money"
    mopay_mpesa = "mopay_mpesa"
    mopay_ecocash = "mopay_ecocash"
    mopay_card = "mopay_card"
    bank_transfer = "bank_transfer"
    bank = "bank"
    cash = "cash"


class PaymentSubmissionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PaymentTransactionStatus(str, enum.Enum):
    pending = "pending"
    successful = "successful"
    failed = "failed"
    timeout = "timeout"
    pending_verification = "pending_verification"


class ListingStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    rented = "rented"
    archived = "archived"


class ListingVerificationStatus(str, enum.Enum):
    unverified = "unverified"
    pending_verification = "pending_verification"
    verified = "verified"
    rejected = "rejected"


class AllowedTenantType(str, enum.Enum):
    student = "student"
    non_student = "non_student"
    both = "both"


class ApplicationStatus(str, enum.Enum):
    inquiry_pending = "inquiry_pending"
    form_sent = "form_sent"
    submitted = "submitted"
    accepted = "accepted"
    pending = "pending"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"
    withdrawn = "withdrawn"
    info_requested = "info_requested"
    contacted = "contacted"
    expired = "expired"


class PreferredResponseMethod(str, enum.Enum):
    phone_call = "phone_call"
    whatsapp = "whatsapp"
    email = "email"
    sms = "sms"


class RequestResponseStatus(str, enum.Enum):
    queued = "queued"
    sent = "sent"
    failed = "failed"
    scaffolded = "scaffolded"


class CallTaskStatus(str, enum.Enum):
    pending_call = "pending_call"
    contacted = "contacted"
    no_answer = "no_answer"


class ViewingRequestStatus(str, enum.Enum):
    pending = "pending"
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class InvitationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    revoked = "revoked"


class TicketStatus(str, enum.Enum):
    open = "open"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class AuditAction(str, enum.Enum):
    create_tenant = "CREATE_TENANT"
    update_tenant = "UPDATE_TENANT"
    create_payment = "CREATE_PAYMENT"
    approve_payment_submission = "APPROVE_PAYMENT_SUBMISSION"
    reject_payment_submission = "REJECT_PAYMENT_SUBMISSION"
    create_occupancy = "CREATE_OCCUPANCY"
    room_transfer = "ROOM_TRANSFER"
    create_room_listing = "CREATE_ROOM_LISTING"
    update_room_listing = "UPDATE_ROOM_LISTING"
    create_support_ticket = "CREATE_SUPPORT_TICKET"
    update_support_ticket = "UPDATE_SUPPORT_TICKET"
    approve_landlord = "APPROVE_LANDLORD"
    issue_lease = "ISSUE_LEASE"
    sign_lease = "SIGN_LEASE"
    verify_listing = "VERIFY_LISTING"
    create_damage_record = "CREATE_DAMAGE_RECORD"
    login_success = "LOGIN_SUCCESS"
    login_failure = "LOGIN_FAILURE"


class LeaseStatus(str, enum.Enum):
    draft = "draft"
    issued = "issued"
    signed = "signed"
    active = "active"
    expired = "expired"
    terminated = "terminated"


class MessageThreadStatus(str, enum.Enum):
    open = "open"
    closed = "closed"


class InspectionType(str, enum.Enum):
    move_in = "move_in"
    move_out = "move_out"


class InspectionStatus(str, enum.Enum):
    draft = "draft"
    completed = "completed"


class DamageStatus(str, enum.Enum):
    reported = "reported"
    verified = "verified"
    charged = "charged"
    waived = "waived"
    repaired = "repaired"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    trialing = "trialing"
    past_due = "past_due"
    cancelled = "cancelled"


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class District(Base, TimestampMixin):
    __tablename__ = "districts"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    rollout_stage: Mapped[str] = mapped_column(String(80), default="locked", index=True)
    description: Mapped[str | None] = mapped_column(Text)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    username: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    preferred_2fa_channel: Mapped[str] = mapped_column(String(40), default="email")
    two_factor_required: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    landlord_profile: Mapped["Landlord | None"] = relationship(back_populates="user")
    caretaker_profile: Mapped["Caretaker | None"] = relationship(back_populates="user")
    tenant_profile: Mapped["Tenant | None"] = relationship(back_populates="user")


class Landlord(Base, TimestampMixin):
    __tablename__ = "landlords"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    business_name: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    system_landlord_number: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    user: Mapped[User] = relationship(back_populates="landlord_profile")
    properties: Mapped[list["Property"]] = relationship(back_populates="landlord")
    caretakers: Mapped[list["Caretaker"]] = relationship(back_populates="landlord")


class LandlordRequestStatus(str, enum.Enum):
    pending = "pending"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"


class LandlordRequest(Base, TimestampMixin):
    __tablename__ = "landlord_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    business_name: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(Text)
    national_id: Mapped[str | None] = mapped_column(String(120))
    selfie_path: Mapped[str | None] = mapped_column(String(500))
    ownership_proof_path: Mapped[str | None] = mapped_column(String(500))
    utility_bill_path: Mapped[str | None] = mapped_column(String(500))
    ownership_document_path: Mapped[str | None] = mapped_column(String(500))
    village_location: Mapped[str | None] = mapped_column(String(160))
    number_of_properties: Mapped[int | None] = mapped_column(Integer)
    number_of_rooms: Mapped[int | None] = mapped_column(Integer)
    emergency_contact: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[LandlordRequestStatus] = mapped_column(Enum(LandlordRequestStatus, name="landlord_request_status"), default=LandlordRequestStatus.pending, index=True)
    admin_note: Mapped[str | None] = mapped_column(Text)
    landlord_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("landlords.id"), nullable=True, index=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Caretaker(Base, TimestampMixin):
    __tablename__ = "caretakers"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))

    user: Mapped[User] = relationship(back_populates="caretaker_profile")
    landlord: Mapped[Landlord] = relationship(back_populates="caretakers")


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("property_categories.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    location_area: Mapped[str] = mapped_column(String(120), index=True)
    address: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(120))
    distance_from_nul: Mapped[str | None] = mapped_column(String(80))

    landlord: Mapped[Landlord] = relationship(back_populates="properties")
    rooms: Mapped[list["Room"]] = relationship(back_populates="property")


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id"), index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("property_categories.id"), nullable=True, index=True)
    room_number: Mapped[str] = mapped_column(String(80))
    status: Mapped[RoomStatus] = mapped_column(Enum(RoomStatus, name="room_status"), default=RoomStatus.vacant, index=True)
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType, name="room_type"))
    room_size: Mapped[str | None] = mapped_column(String(80))
    rent_price: Mapped[float] = mapped_column(Numeric(12, 2))
    deposit_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)

    property: Mapped[Property] = relationship(back_populates="rooms")


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), unique=True, nullable=True)
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_type: Mapped[TenantType] = mapped_column(Enum(TenantType, name="tenant_type"))
    full_name: Mapped[str] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(255))
    national_id: Mapped[str | None] = mapped_column(String(120))
    passport_number: Mapped[str | None] = mapped_column(String(120))
    student_number: Mapped[str | None] = mapped_column(String(120))
    institution: Mapped[str | None] = mapped_column(String(255))
    occupation: Mapped[str | None] = mapped_column(String(255))
    next_of_kin_name: Mapped[str | None] = mapped_column(String(255))
    next_of_kin_phone: Mapped[str | None] = mapped_column(String(40))
    emergency_contact_name: Mapped[str | None] = mapped_column(String(255))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(40))
    verification_status: Mapped[TenantVerificationStatus] = mapped_column(
        Enum(TenantVerificationStatus, name="tenant_verification_status"),
        default=TenantVerificationStatus.pending_verification,
    )
    tenant_status: Mapped[TenantStatus] = mapped_column(Enum(TenantStatus, name="tenant_status"), default=TenantStatus.active, index=True)
    lease_start_date: Mapped[date | None] = mapped_column(Date)
    lease_end_date: Mapped[date | None] = mapped_column(Date)
    monthly_rent: Mapped[float | None] = mapped_column(Numeric(12, 2))
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    deposit_paid: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    outstanding_balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notices: Mapped[str | None] = mapped_column(Text)
    profile_photo_path: Mapped[str | None] = mapped_column(String(500))

    user: Mapped[User | None] = relationship(back_populates="tenant_profile")


class Occupancy(Base, TimestampMixin):
    __tablename__ = "occupancies"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id"), index=True)
    move_in_date: Mapped[date] = mapped_column(Date)
    move_out_date: Mapped[date | None] = mapped_column(Date)
    monthly_rent: Mapped[float] = mapped_column(Numeric(12, 2))
    deposit_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    billing_start_month: Mapped[date] = mapped_column(Date)
    status: Mapped[OccupancyStatus] = mapped_column(Enum(OccupancyStatus, name="occupancy_status"), default=OccupancyStatus.active)


class RentDue(Base, TimestampMixin):
    __tablename__ = "rent_dues"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    occupancy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("occupancies.id"), index=True)
    due_month: Mapped[date] = mapped_column(Date)
    amount_due: Mapped[float] = mapped_column(Numeric(12, 2))
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    due_date: Mapped[date | None] = mapped_column(Date)
    late_penalty_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[RentDueStatus] = mapped_column(Enum(RentDueStatus, name="rent_due_status"), default=RentDueStatus.unpaid)

    __table_args__ = (UniqueConstraint("occupancy_id", "due_month", name="uq_due_occupancy_month"),)


class PaymentSubmission(Base, TimestampMixin):
    __tablename__ = "payment_submissions"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    rent_due_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rent_dues.id"), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"))
    transaction_reference: Mapped[str] = mapped_column(String(160), index=True)
    proof_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[PaymentSubmissionStatus] = mapped_column(
        Enum(PaymentSubmissionStatus, name="payment_submission_status"),
        default=PaymentSubmissionStatus.pending,
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("landlord_id", "transaction_reference", name="uq_landlord_transaction_ref"),)


class PaymentReceipt(Base, TimestampMixin):
    __tablename__ = "payment_receipts"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id"), nullable=True, index=True)
    payment_submission_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payment_submissions.id"), unique=True, nullable=True, index=True)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("landlord_subscriptions.id"), nullable=True, index=True)
    receipt_type: Mapped[str] = mapped_column(String(40), default="rent", index=True)
    receipt_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"))
    transaction_reference: Mapped[str | None] = mapped_column(String(160), index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    pdf_url: Mapped[str | None] = mapped_column(String(500))


class PaymentTransaction(Base, TimestampMixin):
    __tablename__ = "payment_transactions"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    rent_due_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rent_dues.id"), nullable=True, index=True)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("landlord_subscriptions.id"), nullable=True, index=True)
    payment_submission_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payment_submissions.id"), nullable=True, index=True)
    payment_type: Mapped[str] = mapped_column(String(60), default="rent", index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"), index=True)
    payer_phone: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[PaymentTransactionStatus] = mapped_column(Enum(PaymentTransactionStatus, name="payment_transaction_status"), default=PaymentTransactionStatus.pending, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    checkout_request_id: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True, index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True, index=True)
    provider_message: Mapped[str | None] = mapped_column(Text)
    provider_error: Mapped[str | None] = mapped_column(Text)
    webhook_event_id: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True, index=True)
    provider_status: Mapped[str | None] = mapped_column(String(80), index=True)
    verified_signature: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    raw_callback_json: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TwoFactorChallenge(Base, TimestampMixin):
    __tablename__ = "two_factor_challenges"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    channel: Mapped[str] = mapped_column(String(40), default="email", index=True)
    otp_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)


class RoomListing(Base, TimestampMixin):
    __tablename__ = "room_listings"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id"), index=True)
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    rent_price: Mapped[float] = mapped_column(Numeric(12, 2))
    deposit_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType, name="room_type"))
    room_size: Mapped[str | None] = mapped_column(String(80))
    location_area: Mapped[str] = mapped_column(String(120), index=True)
    allowed_tenant_type: Mapped[AllowedTenantType] = mapped_column(Enum(AllowedTenantType, name="allowed_tenant_type"), default=AllowedTenantType.both)
    available_from: Mapped[date | None] = mapped_column(Date)
    distance_from_nul: Mapped[str | None] = mapped_column(String(80))
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    water_available: Mapped[bool] = mapped_column(Boolean, default=False)
    electricity_available: Mapped[bool] = mapped_column(Boolean, default=False)
    internet_included: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    furnished: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    parking_available: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    pets_allowed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    gender_preference: Mapped[str | None] = mapped_column(String(80))
    security_features: Mapped[str | None] = mapped_column(Text)
    house_rules: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ListingStatus] = mapped_column(Enum(ListingStatus, name="listing_status"), default=ListingStatus.draft, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    verification_status: Mapped[ListingVerificationStatus] = mapped_column(Enum(ListingVerificationStatus, name="listing_verification_status"), default=ListingVerificationStatus.unverified, index=True)
    verification_note: Mapped[str | None] = mapped_column(Text)

    room: Mapped[Room] = relationship(viewonly=True)
    listing_property: Mapped[Property] = relationship("Property", viewonly=True)

    @property
    def room_number(self) -> str | None:
        return self.room.room_number if self.room else None

    @property
    def property_name(self) -> str | None:
        return self.listing_property.name if self.listing_property else None


class ListingPhoto(Base, TimestampMixin):
    __tablename__ = "listing_photos"

    id: Mapped[uuid.UUID] = uuid_pk()
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("room_listings.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    caption: Mapped[str | None] = mapped_column(String(255))


class ViewingRequest(Base, TimestampMixin):
    __tablename__ = "viewing_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("room_listings.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(255))
    preferred_date: Mapped[date | None] = mapped_column(Date)
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ViewingRequestStatus] = mapped_column(Enum(ViewingRequestStatus, name="viewing_request_status"), default=ViewingRequestStatus.pending)


class TenantApplication(Base, TimestampMixin):
    __tablename__ = "tenant_applications"

    id: Mapped[uuid.UUID] = uuid_pk()
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("room_listings.id"), index=True)
    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id"), nullable=True, index=True)
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("properties.id"), nullable=True, index=True)
    landlord_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("landlords.id"), nullable=True, index=True)
    applicant_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(40))
    alternative_phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(255))
    national_id: Mapped[str | None] = mapped_column(String(120))
    passport_number: Mapped[str | None] = mapped_column(String(120))
    tenant_type: Mapped[TenantType] = mapped_column(Enum(TenantType, name="tenant_type"))
    student_number: Mapped[str | None] = mapped_column(String(120))
    institution: Mapped[str | None] = mapped_column(String(255))
    occupation: Mapped[str | None] = mapped_column(String(255))
    emergency_contact_name: Mapped[str | None] = mapped_column(String(255))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(40))
    preferred_move_in_date: Mapped[date | None] = mapped_column(Date)
    emergency_contact: Mapped[str | None] = mapped_column(String(255))
    document_path: Mapped[str | None] = mapped_column(String(500))
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus, name="application_status"), default=ApplicationStatus.pending, index=True)
    landlord_note: Mapped[str | None] = mapped_column(Text)
    preferred_response_method: Mapped[PreferredResponseMethod | None] = mapped_column(Enum(PreferredResponseMethod, name="preferred_response_method"), nullable=True)
    response_contact_value: Mapped[str | None] = mapped_column(String(255))
    response_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_status: Mapped[RequestResponseStatus | None] = mapped_column(Enum(RequestResponseStatus, name="request_response_status"), nullable=True)
    application_token: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True, index=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    form_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RequestResponseLog(Base, TimestampMixin):
    __tablename__ = "request_response_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant_applications.id"), index=True)
    recipient_name: Mapped[str] = mapped_column(String(255))
    recipient_phone: Mapped[str | None] = mapped_column(String(40))
    recipient_email: Mapped[str | None] = mapped_column(String(255))
    channel: Mapped[PreferredResponseMethod] = mapped_column(Enum(PreferredResponseMethod, name="preferred_response_method"), index=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[RequestResponseStatus] = mapped_column(Enum(RequestResponseStatus, name="request_response_status"), default=RequestResponseStatus.scaffolded, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RequestCallLog(Base, TimestampMixin):
    __tablename__ = "request_call_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant_applications.id"), index=True)
    caller_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_phone: Mapped[str] = mapped_column(String(40))
    status: Mapped[CallTaskStatus] = mapped_column(Enum(CallTaskStatus, name="call_task_status"), default=CallTaskStatus.pending_call, index=True)


class TenantInvitation(Base, TimestampMixin):
    __tablename__ = "tenant_invitations"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_application_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenant_applications.id"), nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(40), index=True)
    token: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[InvitationStatus] = mapped_column(Enum(InvitationStatus, name="invitation_status"), default=InvitationStatus.pending)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OnboardingChecklist(Base, TimestampMixin):
    __tablename__ = "onboarding_checklists"

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), unique=True, index=True)
    documents_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    deposit_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    first_rent_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    room_assigned: Mapped[bool] = mapped_column(Boolean, default=False)
    keys_issued: Mapped[bool] = mapped_column(Boolean, default=False)
    occupancy_activated: Mapped[bool] = mapped_column(Boolean, default=False)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class NotificationPreference(Base, TimestampMixin):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ReminderLog(Base, TimestampMixin):
    __tablename__ = "reminder_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    landlord_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("landlords.id"), nullable=True, index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("properties.id"), nullable=True, index=True)
    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(40), index=True)
    reminder_type: Mapped[str] = mapped_column(String(80), index=True)
    target_id: Mapped[str] = mapped_column(String(80), index=True)
    scheduled_for: Mapped[date] = mapped_column(Date, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    message: Mapped[str] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("reminder_type", "target_id", "channel", "scheduled_for", name="uq_reminder_target_channel_schedule"),)


class RuleVisibility(str, enum.Enum):
    public = "public"
    private = "private"


class LineRule(Base, TimestampMixin):
    __tablename__ = "line_rules"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    visibility: Mapped[RuleVisibility] = mapped_column(Enum(RuleVisibility, name="rule_visibility"), default=RuleVisibility.public, index=True)


class RuleAcknowledgement(Base, TimestampMixin):
    __tablename__ = "rule_acknowledgements"

    id: Mapped[uuid.UUID] = uuid_pk()
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("line_rules.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("rule_id", "tenant_id", name="uq_rule_acknowledgement"),)


class ComplaintVisibility(str, enum.Enum):
    public = "public"
    private = "private"


class ComplaintStatus(str, enum.Enum):
    open = "open"
    in_review = "in_review"
    resolved = "resolved"


class Complaint(Base, TimestampMixin):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("landlords.id"), nullable=True, index=True)
    sender_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    receiver_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("properties.id"), nullable=True, index=True)
    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    visibility: Mapped[ComplaintVisibility] = mapped_column(Enum(ComplaintVisibility, name="complaint_visibility"), default=ComplaintVisibility.private, index=True)
    status: Mapped[ComplaintStatus] = mapped_column(Enum(ComplaintStatus, name="complaint_status"), default=ComplaintStatus.open, index=True)


class PropertyCategory(Base, TimestampMixin):
    __tablename__ = "property_categories"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("landlord_id", "name", name="uq_property_category_landlord_name"),)


class PasswordResetToken(Base, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    channel: Mapped[str] = mapped_column(String(40), default="email")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LeaseAgreement(Base, TimestampMixin):
    __tablename__ = "lease_agreements"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id"), index=True)
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id"), index=True)
    occupancy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("occupancies.id"), index=True)
    lease_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    monthly_rent: Mapped[float] = mapped_column(Numeric(12, 2))
    deposit_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    terms: Mapped[str | None] = mapped_column(Text)
    status: Mapped[LeaseStatus] = mapped_column(Enum(LeaseStatus, name="lease_status"), default=LeaseStatus.draft, index=True)
    tenant_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    landlord_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pdf_url: Mapped[str | None] = mapped_column(String(500))


class MessageThread(Base, TimestampMixin):
    __tablename__ = "message_threads"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("landlords.id"), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(255))
    application_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenant_applications.id"), nullable=True, index=True)
    support_ticket_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("support_tickets.id"), nullable=True, index=True)
    lease_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("lease_agreements.id"), nullable=True, index=True)
    payment_submission_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payment_submissions.id"), nullable=True, index=True)
    status: Mapped[MessageThreadStatus] = mapped_column(Enum(MessageThreadStatus, name="message_thread_status"), default=MessageThreadStatus.open, index=True)


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("message_threads.id"), index=True)
    sender_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RoomInspection(Base, TimestampMixin):
    __tablename__ = "room_inspections"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id"), index=True)
    occupancy_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("occupancies.id"), nullable=True, index=True)
    inspection_type: Mapped[InspectionType] = mapped_column(Enum(InspectionType, name="inspection_type"), index=True)
    status: Mapped[InspectionStatus] = mapped_column(Enum(InspectionStatus, name="inspection_status"), default=InspectionStatus.draft, index=True)
    room_condition: Mapped[str | None] = mapped_column(Text)
    walls: Mapped[str | None] = mapped_column(Text)
    door_lock: Mapped[str | None] = mapped_column(Text)
    windows: Mapped[str | None] = mapped_column(Text)
    electricity: Mapped[str | None] = mapped_column(Text)
    water: Mapped[str | None] = mapped_column(Text)
    furniture: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DamageRecord(Base, TimestampMixin):
    __tablename__ = "damage_records"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id"), index=True)
    inspection_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("room_inspections.id"), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    estimated_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[DamageStatus] = mapped_column(Enum(DamageStatus, name="damage_status"), default=DamageStatus.reported, index=True)


class SubscriptionPlan(Base, TimestampMixin):
    __tablename__ = "subscription_plans"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120), unique=True)
    monthly_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    max_properties: Mapped[int] = mapped_column(Integer, default=1)
    max_rooms: Mapped[int] = mapped_column(Integer, default=10)
    features: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class LandlordSubscription(Base, TimestampMixin):
    __tablename__ = "landlord_subscriptions"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subscription_plans.id"), index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus, name="subscription_status"), default=SubscriptionStatus.active, index=True)
    start_date: Mapped[date] = mapped_column(Date)
    renewal_date: Mapped[date | None] = mapped_column(Date)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    landlord_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("landlords.id"), nullable=True, index=True)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction, name="audit_action"), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(120))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SupportTicket(Base, TimestampMixin):
    __tablename__ = "support_tickets"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("landlords.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(80))
    priority: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus, name="ticket_status"), default=TicketStatus.open, index=True)


class SupportTicketMessage(Base, TimestampMixin):
    __tablename__ = "support_ticket_messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("support_tickets.id"), index=True)
    sender_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(Text)


class Upload(Base, TimestampMixin):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = uuid_pk()
    landlord_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("landlords.id"), nullable=True, index=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    purpose: Mapped[str] = mapped_column(String(80))
