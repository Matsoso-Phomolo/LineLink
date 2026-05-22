import uuid
from datetime import date, datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    AllowedTenantType,
    ApplicationStatus,
    InvitationStatus,
    ListingStatus,
    PaymentMethod,
    PaymentSubmissionStatus,
    RentDueStatus,
    RoomStatus,
    RoomType,
    TenantType,
    TenantVerificationStatus,
    UserRole,
    ViewingRequestStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    phone: str | None = None
    full_name: str
    password: str = Field(min_length=8)
    role: UserRole


class UserRead(ORMModel):
    id: uuid.UUID
    email: str
    phone: str | None
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


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


class CaretakerCreate(BaseModel):
    user_id: uuid.UUID
    landlord_id: uuid.UUID
    phone: str | None = None


class PropertyBase(BaseModel):
    name: str
    description: str | None = None
    location_area: str
    address: str | None = None
    country: str | None = None
    distance_from_nul: str | None = None


class PropertyCreate(PropertyBase):
    landlord_id: uuid.UUID | None = None


class PropertyRead(PropertyBase, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    created_at: datetime


class RoomBase(BaseModel):
    property_id: uuid.UUID
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
    full_name: str
    phone: str
    email: EmailStr | None = None
    national_id: str | None = None
    passport_number: str | None = None
    student_number: str | None = None
    institution: str | None = None
    occupation: str | None = None
    next_of_kin_name: str | None = None
    next_of_kin_phone: str | None = None


class TenantCreate(TenantBase):
    user_id: uuid.UUID | None = None


class TenantUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    verification_status: TenantVerificationStatus | None = None
    next_of_kin_name: str | None = None
    next_of_kin_phone: str | None = None


class TenantRead(TenantBase, ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    landlord_id: uuid.UUID
    verification_status: TenantVerificationStatus
    profile_photo_path: str | None
    created_at: datetime


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
    amount_due: float
    amount_paid: float
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
    security_features: str | None = None
    house_rules: str | None = None
    status: ListingStatus = ListingStatus.draft
    is_public: bool = False


class ListingCreate(ListingBase):
    pass


class ListingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    rent_price: float | None = None
    deposit_amount: float | None = None
    allowed_tenant_type: AllowedTenantType | None = None
    available_from: date | None = None
    contact_phone: str | None = None
    water_available: bool | None = None
    electricity_available: bool | None = None
    security_features: str | None = None
    house_rules: str | None = None
    status: ListingStatus | None = None
    is_public: bool | None = None


class ListingRead(ListingBase, ORMModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
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
    phone: str
    email: EmailStr | None = None
    tenant_type: TenantType
    student_number: str | None = None
    occupation: str | None = None
    preferred_move_in_date: date | None = None
    emergency_contact: str | None = None
    document_path: str | None = None
    message: str | None = None


class TenantApplicationRead(TenantApplicationCreate, ORMModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    applicant_user_id: uuid.UUID | None
    status: ApplicationStatus
    landlord_note: str | None
    created_at: datetime


class ApplicationDecision(BaseModel):
    landlord_note: str | None = None


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
