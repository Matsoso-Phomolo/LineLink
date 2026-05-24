export type Role = "admin" | "landlord" | "caretaker" | "tenant";

export type User = {
  id: string;
  username?: string | null;
  email: string;
  phone?: string | null;
  full_name: string;
  role: Role;
  is_active: boolean;
  must_change_password: boolean;
  created_at: string;
};

export type DashboardSummary = {
  properties: number;
  rooms: number;
  vacant_rooms: number;
  occupied_rooms: number;
  active_tenants: number;
  unpaid_rent_dues: number;
  pending_payment_submissions: number;
  published_listings: number;
  pending_applications: number;
  pending_room_requests: number;
  maintenance_tickets: number;
  overdue_rent_dues: number;
  active_landlords: number;
  pending_landlord_requests: number;
  total_tenants: number;
};

export type PropertyItem = {
  id: string;
  landlord_id: string;
  category_id?: string | null;
  name: string;
  description?: string | null;
  location_area: string;
  address?: string | null;
  country?: string | null;
  distance_from_nul?: string | null;
  created_at?: string;
};

export type Room = {
  id: string;
  landlord_id: string;
  property_id: string;
  room_number: string;
  status: "vacant" | "occupied" | "maintenance";
  room_type: "single" | "double";
  room_size?: string | null;
  rent_price: number;
  deposit_amount: number;
  notes?: string | null;
  category_id?: string | null;
};

export type Listing = {
  id: string;
  landlord_id: string;
  property_id: string;
  room_id: string;
  room_number?: string | null;
  property_name?: string | null;
  title: string;
  description?: string | null;
  rent_price: number;
  deposit_amount: number;
  room_type: "single" | "double";
  room_size?: string | null;
  location_area: string;
  allowed_tenant_type: "student" | "non_student" | "both";
  distance_from_nul?: string | null;
  contact_phone?: string | null;
  water_available: boolean;
  electricity_available: boolean;
  internet_included: boolean;
  furnished: boolean;
  parking_available: boolean;
  pets_allowed: boolean;
  gender_preference?: string | null;
  security_features?: string | null;
  house_rules?: string | null;
  status: "draft" | "published" | "rented" | "archived";
  is_public: boolean;
  is_verified: boolean;
  verification_status?: "unverified" | "pending_verification" | "verified" | "rejected";
  verification_note?: string | null;
};

export type TenantApplication = {
  id: string;
  listing_id: string;
  room_id?: string | null;
  property_id?: string | null;
  landlord_id?: string | null;
  applicant_user_id?: string | null;
  full_name: string;
  gender?: string | null;
  phone: string;
  alternative_phone?: string | null;
  email?: string | null;
  national_id?: string | null;
  passport_number?: string | null;
  tenant_type: "student" | "non_student";
  student_number?: string | null;
  institution?: string | null;
  occupation?: string | null;
  preferred_move_in_date?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  emergency_contact?: string | null;
  document_path?: string | null;
  message?: string | null;
  status: "inquiry_pending" | "form_sent" | "submitted" | "accepted" | "pending" | "under_review" | "approved" | "rejected" | "withdrawn" | "info_requested" | "contacted" | "expired";
  landlord_note?: string | null;
  preferred_response_method?: "phone_call" | "whatsapp" | "email" | "sms" | null;
  response_contact_value?: string | null;
  response_sent_at?: string | null;
  response_status?: "queued" | "sent" | "failed" | "scaffolded" | null;
  application_token?: string | null;
  token_expires_at?: string | null;
  form_sent_at?: string | null;
  submitted_at?: string | null;
  created_at: string;
};

export type RequestResponseLog = {
  id: string;
  request_id: string;
  recipient_name: string;
  recipient_phone?: string | null;
  recipient_email?: string | null;
  channel: "phone_call" | "whatsapp" | "email" | "sms";
  message: string;
  status: "queued" | "sent" | "failed" | "scaffolded";
  sent_at?: string | null;
  created_at: string;
};

export type Landlord = {
  id: string;
  user_id: string;
  business_name?: string | null;
  contact_phone?: string | null;
  email?: string | null;
  address?: string | null;
  system_landlord_number?: string | null;
  is_active: boolean;
};

export type LandlordRequest = {
  id: string;
  business_name: string;
  full_name: string;
  email: string;
  phone?: string | null;
  address?: string | null;
  message?: string | null;
  status: "pending" | "approved" | "rejected";
  admin_note?: string | null;
  landlord_id?: string | null;
  approved_by_user_id?: string | null;
  approved_at?: string | null;
  created_at: string;
};

export type Caretaker = {
  id: string;
  user_id: string;
  landlord_id: string;
  phone?: string | null;
  username?: string | null;
  full_name: string;
  email: string;
  is_active: boolean;
  created_at: string;
};

export type Tenant = {
  id: string;
  user_id?: string | null;
  landlord_id: string;
  tenant_type: "student" | "non_student";
  full_name: string;
  gender?: string | null;
  phone: string;
  email?: string | null;
  national_id?: string | null;
  passport_number?: string | null;
  occupation?: string | null;
  next_of_kin_name?: string | null;
  next_of_kin_phone?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  tenant_status?: "active" | "overdue" | "moved_out" | "disabled";
  lease_start_date?: string | null;
  lease_end_date?: string | null;
};

export type PaymentSubmission = {
  id: string;
  tenant_id: string;
  rent_due_id?: string | null;
  amount: number;
  method: "mpesa" | "ecocash" | "orange_money" | "bank_transfer" | "bank" | "cash";
  transaction_reference: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
};

export type PaymentTransaction = {
  id: string;
  rent_due_id?: string | null;
  tenant_id: string;
  amount: number;
  method: "mpesa" | "ecocash" | "orange_money" | "bank_transfer" | "bank" | "cash";
  payer_phone?: string | null;
  status: "pending" | "successful" | "failed" | "timeout" | "pending_verification";
  idempotency_key: string;
  checkout_request_id?: string | null;
  provider_reference?: string | null;
  provider_message?: string | null;
  provider_error?: string | null;
  created_at: string;
};

export type SupportTicket = {
  id: string;
  tenant_id: string;
  title: string;
  category: string;
  priority?: string | null;
  description: string;
  assigned_to_user_id?: string | null;
  resolved_at?: string | null;
  status: "open" | "assigned" | "in_progress" | "resolved" | "closed";
  created_at: string;
};

export type NotificationItem = {
  id: string;
  title: string;
  body: string;
  category: string;
  is_read: boolean;
  created_at: string;
};

export type LeaseAgreement = {
  id: string;
  lease_number: string;
  landlord_id: string;
  tenant_id: string;
  property_id: string;
  room_id: string;
  occupancy_id: string;
  start_date: string;
  end_date?: string | null;
  monthly_rent: number;
  deposit_amount: number;
  terms?: string | null;
  status: "draft" | "issued" | "signed" | "active" | "expired" | "terminated";
  tenant_signed_at?: string | null;
  landlord_signed_at?: string | null;
  pdf_url?: string | null;
  created_at: string;
};

export type PaymentReceipt = {
  id: string;
  receipt_number: string;
  tenant_id: string;
  room_id?: string | null;
  payment_submission_id: string;
  amount: number;
  method: string;
  transaction_reference?: string | null;
  issued_at: string;
  pdf_url?: string | null;
};

export type SubscriptionPlan = {
  id: string;
  name: string;
  monthly_price: number;
  max_properties: number;
  max_rooms: number;
  features?: string | null;
  is_active: boolean;
  created_at: string;
};
