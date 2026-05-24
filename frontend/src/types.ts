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
  name: string;
  description?: string | null;
  location_area: string;
  address?: string | null;
  country?: string | null;
  distance_from_nul?: string | null;
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
  security_features?: string | null;
  house_rules?: string | null;
  status: "draft" | "published" | "rented" | "archived";
  is_public: boolean;
  is_verified: boolean;
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
  status: "inquiry_pending" | "form_sent" | "submitted" | "pending" | "under_review" | "approved" | "rejected" | "withdrawn" | "info_requested" | "expired";
  landlord_note?: string | null;
  application_token?: string | null;
  token_expires_at?: string | null;
  form_sent_at?: string | null;
  submitted_at?: string | null;
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
