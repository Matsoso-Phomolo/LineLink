import uuid
from datetime import date, datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import (
    AllowedTenantType,
    ApplicationStatus,
    ComplaintStatus,
    ComplaintVisibility,
    InvitationStatus,
    LandlordRequestStatus,
    ListingStatus,
    ListingVerificationStatus,
    LeaseStatus,
    MessageThreadStatus,
    InspectionStatus,
    InspectionType,
    DamageStatus,
    SubscriptionStatus,
    PaymentMethod,
    PaymentSubmissionStatus,
    PaymentTransactionStatus,
    PreferredResponseMethod,
    RequestResponseStatus,
    RentDueStatus,
    RoomStatus,
    RoomType,
    RuleVisibility,
    TenantStatus,
    TenantType,
    TenantVerificationStatus,
    UserRole,
    ViewingRequestStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    requires_2fa: bool = False
    challenge_id: uuid.UUID | None = None
    channel: str | None = None
    demo_otp: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    phone: str | None = None
    full_name: str
    password: str = Field(min_length=8)
    role: UserRole


class UserRead(ORMModel):
    id: uuid.UUID
    username: str | None = None
    email: str
    phone: str | None
    full_name: str
    role: UserRole
    is_active: bool
    must_change_password: bool = False
    two_factor_enabled: bool = False
    preferred_2fa_channel: str | None = None
    two_factor_required: bool = False
    created_at: datetime


class PasswordResetRequest(BaseModel):
    identifier: str
    channel: str = "email"


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class AdminPasswordReset(BaseModel):
    identifier: str
    new_password: str = Field(min_length=8)
    must_change_password: bool = False


class LandlordCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID
    business_name: str | None = Field(default=None, validation_alias=AliasChoices("business_name", "name"))
    contact_phone: str | None = Field(default=None, validation_alias=AliasChoices("contact_phone", "phone"))
    email: EmailStr | None = None
    address: str | None = None


class LandlordRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    business_name: str | None
    contact_phone: str | None
    email: EmailStr | None
    address: str | None
    system_landlord_number: str | None = None
    is_active: bool = True


class LandlordRequestPropertyCreate(BaseModel):
    property_name: str
    district_id: uuid.UUID
    area_id: uuid.UUID
    village_location: str
    address: str | None = None
    description: str | None = None

    total_rooms: int = Field(gt=0)
    single_rooms: int = Field(ge=0)
    double_rooms: int = Field(ge=0)

    single_room_prefix: str = "A"
    double_room_prefix: str = "B"
    starting_room_number: int = 101

    single_room_rent: float | None = None
    double_room_rent: float | None = None

    @model_validator(mode="after")
    def validate_room_counts(self):
        if self.single_rooms + self.double_rooms != self.total_rooms:
            raise ValueError("single_rooms + double_rooms must equal total_rooms")

        self.single_room_prefix = self.single_room_prefix.strip().upper()
        self.double_room_prefix = self.double_room_prefix.strip().upper()

        if not self.single_room_prefix or not self.double_room_prefix:
            raise ValueError("single and double room prefixes are required")

        if self.single_room_prefix == self.double_room_prefix:
            raise ValueError("single and double room prefixes must differ")

        return self


class LandlordRequestPropertyRead(LandlordRequestPropertyCreate, ORMModel):
    id: uuid.UUID
    landlord_request_id: uuid.UUID
    created_at: datetime


class LandlordRequestCreate(BaseModel):
    business_name: str | None = None
    full_name: str
    email: EmailStr
    phone: str | None = None
    address: str
    preferred_response_method: PreferredResponseMethod
    response_contact_value: str
    emergency_contact: str | None = None
    message: str | None = None


class LandlordManualCreate(BaseModel):
    business_name: str
    full_name: str
    email: EmailStr
    phone: str | None = None
    address: str | None = None
    password: str = Field(min_length=8)


class LandlordRequestDecision(BaseModel):
    admin_note: str | None = None
    password: str | None = Field(default=None, min_length=8)


class LandlordVerificationCreate(BaseModel):
    email: EmailStr
    national_id: str
    selfie_path: str | None = None
    utility_bill_path: str | None = None
    ownership_document_path: str | None = None
    business_registration_path: str | None = None
    additional_notes: str | None = None
    properties: list[LandlordRequestPropertyCreate] = Field(default_factory=list)


class LandlordVerificationReview(BaseModel):
    admin_note: str | None = None


class LandlordVerificationAIResult(BaseModel):
    recommendation: str
    confidence_score: float
    risk_flags: list[str] = []
    summary: str | None = None


class DistrictSubscriptionPermissionUpdate(BaseModel):
    district_admin_user_id: uuid.UUID
    can_manage_subscriptions: bool


class SubscriptionPricingRuleUpsert(BaseModel):
    district_id: uuid.UUID | None = None
    tier_name: str
    min_rooms: int = Field(gt=0)
    max_rooms: int | None = Field(default=None, gt=0)
    monthly_amount: float = Field(ge=0)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_range(self):
        if self.max_rooms is not None and self.max_rooms < self.min_rooms:
            raise ValueError("max_rooms must be greater than or equal to min_rooms")
        return self


class SubscriptionPricingRuleRead(SubscriptionPricingRuleUpsert, ORMModel):
    id: uuid.UUID
    created_by_user_id: uuid.UUID | None = None
    updated_by_user_id: uuid.UUID | None = None
    created_at: datetime


class PropertySubscriptionCalculation(BaseModel):
    property_id: uuid.UUID
    total_rooms: int
    monthly_subscription_amount: float
    pricing_tier: str


class LandlordRequestRead(LandlordRequestCreate, ORMModel):
    id: uuid.UUID
    status: LandlordRequestStatus
    admin_note: str | None
    landlord_id: uuid.UUID | None
    approved_by_user_id: uuid.UUID | None
    approved_at: datetime | None
    verification_token: str | None = None
    verification_token_expires_at: datetime | None = None
    verification_url: str | None = None
    ai_recommendation: str | None = None
    ai_confidence_score: float | None = None
    ai_summary: str | None = None
    ai_risk_flags: str | None = None
    created_at: datetime
    properties: list[LandlordRequestPropertyRead] = Field(default_factory=list)


class LandlordOnboardingResult(BaseModel):
    request: LandlordRequestRead | None = None
    landlord: LandlordRead
    temporary_password: str | None = None


class CaretakerCreate(BaseModel):
    user_id: uuid.UUID
    landlord_id: uuid.UUID
    phone: str | None = None


class CaretakerAccountCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8)


class CaretakerUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    is_active: bool | None = None


class CaretakerRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    landlord_id: uuid.UUID
    phone: str | None = None
    username: str | None = None
    full_name: str
    email: str
    is_active: bool
    created_at: datetime


class PropertyBase(BaseModel):
    name: str
    description: str | None = None
    location_area: str
    address: str | None = None
    country: str | None = None
    distance_from_nul: str | None = None


class PropertyCreate(PropertyBase):
    landlord_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    district_id: uuid.UUID
    area_id: uuid.UUID


class PropertyUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    name: str | None = None
    description: str | None = None
    location_area: str | None = None
    address: str | None = None
    country: str | None = None
    distance_from_nul: str | None = None


class PropertyRead(PropertyBase, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    category_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    created_at: datetime


class RoomBase(BaseModel):
    property_id: uuid.UUID
    category_id: uuid.UUID | None = None
    room_number: str
    status: RoomStatus = RoomStatus.vacant
    room_type: RoomType
    room_size: str | None = None
    rent_price: float
    deposit_amount: float = 0
    notes: str | None = None


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    room_number: str | None = None
    status: RoomStatus | None = None
    room_type: RoomType | None = None
    room_size: str | None = None
    rent_price: float | None = None
    deposit_amount: float | None = None
    notes: str | None = None


class RoomRead(RoomBase, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    created_at: datetime


class TenantBase(BaseModel):
    tenant_type: TenantType
    tenant_category: str | None = None
    tenant_subtype: str | None = None
    full_name: str
    gender: str | None = None
    phone: str
    email: EmailStr | None = None
    national_id: str | None = None
    passport_number: str | None = None
    student_number: str | None = None
    institution: str | None = None
    institution_name: str | None = None
    sponsor_or_guardian_name: str | None = None
    occupation: str | None = None
    employer_or_business_name: str | None = None
    work_location: str | None = None
    number_of_occupants: int | None = None
    children_count: int | None = None
    parking_required: bool | None = None
    funding_source: str | None = None
    guarantor_name: str | None = None
    additional_notes: str | None = None
    next_of_kin_name: str | None = None
    next_of_kin_phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

    @model_validator(mode="after")
    def normalize_profile(self):
        if not self.tenant_category:
            self.tenant_category = "student" if self.tenant_type == TenantType.student else "worker"
        else:
            self.tenant_category = self.tenant_category.strip().lower()
        if self.tenant_subtype:
            self.tenant_subtype = self.tenant_subtype.strip().lower()
        if self.tenant_category != "student" and self.tenant_type == TenantType.student:
            self.tenant_type = TenantType.non_student
        if self.tenant_category == "student":
            self.tenant_type = TenantType.student
            if self.institution_name and not self.institution:
                self.institution = self.institution_name
        return self


class TenantCreate(TenantBase):
    user_id: uuid.UUID | None = None


class TenantAccountCreate(TenantBase):
    room_id: uuid.UUID | None = None
    lease_start_date: date | None = None
    lease_end_date: date | None = None
    monthly_rent: float | None = None
    deposit_amount: float | None = None


class TenantUpdate(BaseModel):
    full_name: str | None = None
    gender: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    national_id: str | None = None
    passport_number: str | None = None
    tenant_type: TenantType | None = None
    tenant_category: str | None = None
    tenant_subtype: str | None = None
    student_number: str | None = None
    institution: str | None = None
    institution_name: str | None = None
    sponsor_or_guardian_name: str | None = None
    occupation: str | None = None
    employer_or_business_name: str | None = None
    work_location: str | None = None
    number_of_occupants: int | None = None
    children_count: int | None = None
    parking_required: bool | None = None
    funding_source: str | None = None
    guarantor_name: str | None = None
    additional_notes: str | None = None
    verification_status: TenantVerificationStatus | None = None
    tenant_status: TenantStatus | None = None
    lease_start_date: date | None = None
    lease_end_date: date | None = None
    monthly_rent: float | None = None
    deposit_amount: float | None = None
    deposit_paid: bool | None = None
    outstanding_balance: float | None = None
    notices: str | None = None
    next_of_kin_name: str | None = None
    next_of_kin_phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

    @model_validator(mode="after")
    def normalize_profile(self):
        if self.tenant_category:
            self.tenant_category = self.tenant_category.strip().lower()
            if self.tenant_category == "student":
                self.tenant_type = TenantType.student
                if self.institution_name and not self.institution:
                    self.institution = self.institution_name
            elif self.tenant_category in {"worker", "family", "other"}:
                self.tenant_type = TenantType.non_student
        elif self.tenant_type and not self.tenant_category:
            self.tenant_category = "student" if self.tenant_type == TenantType.student else "worker"
        if self.tenant_subtype:
            self.tenant_subtype = self.tenant_subtype.strip().lower()
        return self


class TenantRead(TenantBase, ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    landlord_id: uuid.UUID
    verification_status: TenantVerificationStatus
    tenant_status: TenantStatus = TenantStatus.active
    lease_start_date: date | None = None
    lease_end_date: date | None = None
    monthly_rent: float | None = None
    deposit_amount: float | None = None
    deposit_paid: bool = False
    outstanding_balance: float = 0
    notices: str | None = None
    profile_photo_path: str | None
    created_at: datetime


class TenantAccountResult(BaseModel):
    tenant: TenantRead
    username: str
    temporary_password: str


class OccupancyCreate(BaseModel):
    tenant_id: uuid.UUID
    room_id: uuid.UUID
    move_in_date: date
    monthly_rent: float
    deposit_amount: float = 0
    billing_start_month: date


class OccupancyRead(ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    tenant_id: uuid.UUID
    room_id: uuid.UUID
    move_in_date: date
    move_out_date: date | None
    monthly_rent: float
    deposit_amount: float
    billing_start_month: date
    status: str


class RentDueRead(ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    tenant_id: uuid.UUID
    occupancy_id: uuid.UUID
    due_month: date
    due_date: date | None = None
    amount_due: float
    amount_paid: float
    late_penalty_amount: float = 0
    is_late: bool = False
    status: RentDueStatus


class PaymentSubmissionCreate(BaseModel):
    tenant_id: uuid.UUID
    rent_due_id: uuid.UUID | None = None
    amount: float
    method: PaymentMethod
    transaction_reference: str
    proof_path: str | None = None


class PaymentSubmissionRead(PaymentSubmissionCreate, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    status: PaymentSubmissionStatus
    approved_by_user_id: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime


class PaymentReceiptRead(ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    room_id: uuid.UUID | None = None
    payment_submission_id: uuid.UUID | None = None
    subscription_id: uuid.UUID | None = None
    receipt_type: str = "rent"
    receipt_number: str
    amount: float
    method: PaymentMethod
    transaction_reference: str | None = None
    issued_at: datetime
    pdf_path: str | None = None
    pdf_url: str | None = None


class PaymentInitiateRequest(BaseModel):
    rent_due_id: uuid.UUID | None = None
    amount: float
    method: PaymentMethod
    payer_phone: str | None = None
    tenant_id: uuid.UUID | None = None
    idempotency_key: str | None = None


class PaymentInitiateResponse(ORMModel):
    id: uuid.UUID
    rent_due_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    subscription_id: uuid.UUID | None = None
    payment_type: str = "rent"
    amount: float
    method: PaymentMethod
    payer_phone: str | None = None
    status: PaymentTransactionStatus
    idempotency_key: str
    checkout_request_id: str | None = None
    provider_reference: str | None = None
    provider_status: str | None = None
    webhook_event_id: str | None = None
    verified_signature: bool = False
    processed_at: datetime | None = None
    failure_reason: str | None = None
    provider_message: str | None = None
    provider_error: str | None = None
    created_at: datetime


class PaymentCallbackPayload(BaseModel):
    checkout_request_id: str | None = None
    provider_reference: str | None = None
    idempotency_key: str | None = None
    status: str
    amount: float | None = None
    transaction_reference: str | None = None
    message: str | None = None
    error_message: str | None = None


class TwoFactorVerifyRequest(BaseModel):
    challenge_id: uuid.UUID
    otp: str


class TwoFactorResendRequest(BaseModel):
    challenge_id: uuid.UUID


class TwoFactorSetupRequest(BaseModel):
    channel: str = "email"
    enabled: bool = True


class SubscriptionPayRequest(BaseModel):
    subscription_id: uuid.UUID | None = None
    plan_id: uuid.UUID | None = None
    amount: float
    method: PaymentMethod
    payer_phone: str | None = None
    idempotency_key: str | None = None


class ListingBase(BaseModel):
    property_id: uuid.UUID
    room_id: uuid.UUID
    title: str
    description: str | None = None
    rent_price: float
    deposit_amount: float = 0
    room_type: RoomType
    room_size: str | None = None
    location_area: str
    allowed_tenant_type: AllowedTenantType = AllowedTenantType.both
    available_from: date | None = None
    distance_from_nul: str | None = None
    contact_phone: str | None = None
    water_available: bool = False
    electricity_available: bool = False
    internet_included: bool = False
    furnished: bool = False
    parking_available: bool = False
    pets_allowed: bool = False
    gender_preference: str | None = None
    security_features: str | None = None
    house_rules: str | None = None
    status: ListingStatus = ListingStatus.draft
    is_public: bool = False
    is_verified: bool = False
    verification_status: ListingVerificationStatus = ListingVerificationStatus.unverified
    verification_note: str | None = None


class ListingCreate(ListingBase):
    district_id: uuid.UUID
    area_id: uuid.UUID


class ListingUpdate(BaseModel):
    property_id: uuid.UUID | None = None
    room_id: uuid.UUID | None = None
    district_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    title: str | None = None
    description: str | None = None
    rent_price: float | None = None
    deposit_amount: float | None = None
    room_type: RoomType | None = None
    room_size: str | None = None
    location_area: str | None = None
    allowed_tenant_type: AllowedTenantType | None = None
    available_from: date | None = None
    contact_phone: str | None = None
    water_available: bool | None = None
    electricity_available: bool | None = None
    internet_included: bool | None = None
    furnished: bool | None = None
    parking_available: bool | None = None
    pets_allowed: bool | None = None
    gender_preference: str | None = None
    security_features: str | None = None
    house_rules: str | None = None
    status: ListingStatus | None = None
    is_public: bool | None = None
    is_verified: bool | None = None
    verification_status: ListingVerificationStatus | None = None
    verification_note: str | None = None


class ListingRead(ListingBase, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    district_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    room_number: str | None = None
    property_name: str | None = None
    created_at: datetime


class ListingPhotoRead(ORMModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    file_path: str
    caption: str | None


class ViewingRequestCreate(BaseModel):
    full_name: str
    phone: str
    email: EmailStr | None = None
    preferred_date: date | None = None
    message: str | None = None


class ViewingRequestRead(ViewingRequestCreate, ORMModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    status: ViewingRequestStatus
    created_at: datetime


class TenantApplicationCreate(BaseModel):
    full_name: str
    gender: str | None = None
    phone: str
    alternative_phone: str | None = None
    email: EmailStr | None = None
    national_id: str | None = None
    passport_number: str | None = None
    tenant_type: TenantType
    tenant_category: str | None = None
    tenant_subtype: str | None = None
    student_number: str | None = None
    institution: str | None = None
    institution_name: str | None = None
    sponsor_or_guardian_name: str | None = None
    occupation: str | None = None
    employer_or_business_name: str | None = None
    work_location: str | None = None
    number_of_occupants: int | None = None
    children_count: int | None = None
    parking_required: bool | None = None
    funding_source: str | None = None
    guarantor_name: str | None = None
    additional_notes: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    preferred_move_in_date: date | None = None
    emergency_contact: str | None = None
    document_path: str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def normalize_profile(self):
        if not self.tenant_category:
            self.tenant_category = "student" if self.tenant_type == TenantType.student else "worker"
        else:
            self.tenant_category = self.tenant_category.strip().lower()
        if self.tenant_subtype:
            self.tenant_subtype = self.tenant_subtype.strip().lower()
        if self.tenant_category == "student":
            self.tenant_type = TenantType.student
            if self.institution_name and not self.institution:
                self.institution = self.institution_name
        else:
            self.tenant_type = TenantType.non_student
        return self


class RoomInquiryCreate(BaseModel):
    full_name: str
    phone: str
    email: EmailStr | None = None
    preferred_response_method: PreferredResponseMethod
    message: str | None = None


class PublicApplicationSubmit(TenantApplicationCreate):
    pass


class TenantApplicationRead(TenantApplicationCreate, ORMModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    room_id: uuid.UUID | None = None
    property_id: uuid.UUID | None = None
    landlord_id: uuid.UUID | None = None
    applicant_user_id: uuid.UUID | None
    status: ApplicationStatus
    landlord_note: str | None
    preferred_response_method: PreferredResponseMethod | None = None
    response_contact_value: str | None = None
    response_sent_at: datetime | None = None
    response_status: RequestResponseStatus | None = None
    application_token: str | None = None
    token_expires_at: datetime | None = None
    form_sent_at: datetime | None = None
    submitted_at: datetime | None = None
    created_at: datetime


class ApplicationFormLink(BaseModel):
    application_id: uuid.UUID
    application_url: str
    token_expires_at: datetime


class ApplicationDecision(BaseModel):
    landlord_note: str | None = None


class PublicRequestResponse(BaseModel):
    message: str


class RequestResponseLogRead(ORMModel):
    id: uuid.UUID
    request_id: uuid.UUID
    recipient_name: str
    recipient_phone: str | None = None
    recipient_email: str | None = None
    channel: PreferredResponseMethod
    message: str
    status: RequestResponseStatus
    sent_at: datetime | None = None
    created_at: datetime


class ApplicationAssignRoom(BaseModel):
    move_in_date: date
    monthly_rent: float
    deposit_amount: float = 0
    billing_start_month: date
    create_invitation_if_no_user: bool = True


class TenantInvitationCreate(BaseModel):
    tenant_application_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    email: EmailStr | None = None
    phone: str | None = None


class TenantInvitationAccept(BaseModel):
    token: str
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8)


class TenantInvitationRead(ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    tenant_application_id: uuid.UUID | None
    tenant_id: uuid.UUID | None
    email: EmailStr | None
    phone: str | None
    token: str
    status: InvitationStatus
    expires_at: datetime | None


class UploadRead(ORMModel):
    id: uuid.UUID
    file_path: str
    original_filename: str
    content_type: str
    purpose: str


class NotificationRead(ORMModel):
    id: uuid.UUID
    title: str
    body: str
    category: str
    is_read: bool
    created_at: datetime


class DashboardSummary(BaseModel):
    properties: int
    rooms: int
    vacant_rooms: int
    occupied_rooms: int
    active_tenants: int
    unpaid_rent_dues: int
    pending_payment_submissions: int
    published_listings: int
    pending_applications: int
    pending_room_requests: int = 0
    maintenance_tickets: int = 0
    overdue_rent_dues: int = 0
    active_landlords: int = 0
    pending_landlord_requests: int = 0
    total_tenants: int = 0


class DistrictBase(BaseModel):
    name: str
    slug: str
    is_active: bool = False
    rollout_stage: str = "locked"
    description: str | None = None
    activated_at: datetime | None = None


class DistrictCreate(DistrictBase):
    pass


class DistrictUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    is_active: bool | None = None
    rollout_stage: str | None = None
    description: str | None = None
    activated_at: datetime | None = None


class DistrictResponse(DistrictBase, ORMModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DistrictSeedResponse(BaseModel):
    message: str
    total_districts: int
    active_districts: int
    locked_districts: int


class DistrictAreaBase(BaseModel):
    district_id: uuid.UUID
    name: str
    description: str | None = None
    is_active: bool = True


class DistrictAreaCreate(DistrictAreaBase):
    pass


class DistrictAreaUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class DistrictAreaResponse(ORMModel):
    id: uuid.UUID
    district_id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class PropertyCategoryCreate(BaseModel):
    name: str
    description: str | None = None


class PropertyCategoryRead(PropertyCategoryCreate, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    created_at: datetime


class LineRuleCreate(BaseModel):
    tenant_id: uuid.UUID | None = None
    title: str
    content: str
    visibility: RuleVisibility = RuleVisibility.public


class LineRuleRead(LineRuleCreate, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    created_at: datetime


class ComplaintCreate(BaseModel):
    receiver_user_id: uuid.UUID | None = None
    property_id: uuid.UUID | None = None
    room_id: uuid.UUID | None = None
    title: str
    description: str
    visibility: ComplaintVisibility = ComplaintVisibility.private


class ComplaintUpdate(BaseModel):
    status: ComplaintStatus | None = None


class ComplaintRead(ComplaintCreate, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID | None = None
    sender_user_id: uuid.UUID
    status: ComplaintStatus
    created_at: datetime


class LeaseAgreementRead(ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    tenant_id: uuid.UUID
    property_id: uuid.UUID
    room_id: uuid.UUID
    occupancy_id: uuid.UUID
    lease_number: str
    start_date: date
    end_date: date | None = None
    monthly_rent: float
    deposit_amount: float
    terms: str | None = None
    status: LeaseStatus
    tenant_signed_at: datetime | None = None
    landlord_signed_at: datetime | None = None
    pdf_url: str | None = None
    created_at: datetime


class LeaseUpdate(BaseModel):
    end_date: date | None = None
    terms: str | None = None
    status: LeaseStatus | None = None


class MessageThreadCreate(BaseModel):
    subject: str
    application_id: uuid.UUID | None = None
    support_ticket_id: uuid.UUID | None = None
    lease_id: uuid.UUID | None = None
    payment_submission_id: uuid.UUID | None = None


class MessageThreadRead(MessageThreadCreate, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID | None = None
    status: MessageThreadStatus
    created_at: datetime


class MessageCreate(BaseModel):
    body: str


class MessageRead(MessageCreate, ORMModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    sender_user_id: uuid.UUID
    read_at: datetime | None = None
    created_at: datetime


class RoomInspectionCreate(BaseModel):
    tenant_id: uuid.UUID | None = None
    room_id: uuid.UUID
    occupancy_id: uuid.UUID | None = None
    inspection_type: InspectionType
    room_condition: str | None = None
    walls: str | None = None
    door_lock: str | None = None
    windows: str | None = None
    electricity: str | None = None
    water: str | None = None
    furniture: str | None = None
    notes: str | None = None


class RoomInspectionRead(RoomInspectionCreate, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    status: InspectionStatus
    completed_at: datetime | None = None
    created_at: datetime


class DamageRecordCreate(BaseModel):
    tenant_id: uuid.UUID | None = None
    room_id: uuid.UUID
    inspection_id: uuid.UUID | None = None
    description: str
    estimated_cost: float = 0


class DamageRecordRead(DamageRecordCreate, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    status: DamageStatus
    created_at: datetime


class SubscriptionPlanCreate(BaseModel):
    name: str
    monthly_price: float = 0
    max_properties: int = 1
    max_rooms: int = 10
    features: str | None = None
    is_active: bool = True


class SubscriptionPlanRead(SubscriptionPlanCreate, ORMModel):
    id: uuid.UUID
    created_at: datetime


class LandlordSubscriptionCreate(BaseModel):
    landlord_id: uuid.UUID
    plan_id: uuid.UUID
    status: SubscriptionStatus = SubscriptionStatus.active
    start_date: date
    renewal_date: date | None = None


class LandlordSubscriptionRead(LandlordSubscriptionCreate, ORMModel):
    id: uuid.UUID
    created_at: datetime
