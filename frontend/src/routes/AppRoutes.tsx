import { Navigate, Route, Routes } from "react-router-dom";
import { lazy, Suspense } from "react";
import { AppLayout } from "../layouts/AppLayout";
import { ProtectedRoute } from "./ProtectedRoute";
import { LoginPage } from "../pages/LoginPage";
import { useAuth } from "../auth/AuthContext";

const ForgotPasswordPage = lazy(() =>
  import("../pages/ForgotPasswordPage").then((module) => ({
    default: module.ForgotPasswordPage,
  }))
);

const ChangePasswordPage = lazy(() =>
  import("../pages/ChangePasswordPage").then((module) => ({
    default: module.ChangePasswordPage,
  }))
);

const SecurityPage = lazy(() =>
  import("../pages/SecurityPage").then((module) => ({
    default: module.SecurityPage,
  }))
);

const PublicRoomFinderPage = lazy(() =>
  import("../pages/public/PublicRoomFinderPage").then((module) => ({
    default: module.PublicRoomFinderPage,
  }))
);

const ApplicationFormPage = lazy(() =>
  import("../pages/public/ApplicationFormPage").then((module) => ({
    default: module.ApplicationFormPage,
  }))
);

const LandlordRequestPage = lazy(() =>
  import("../pages/public/LandlordRequestPage").then((module) => ({
    default: module.LandlordRequestPage,
  }))
);

const LandlordVerificationPage = lazy(() =>
  import("../pages/public/LandlordVerificationPage").then((module) => ({
    default: module.LandlordVerificationPage,
  }))
);

const LandlordDashboardPage = lazy(() =>
  import("../pages/landlord/LandlordDashboardPage").then((module) => ({
    default: module.LandlordDashboardPage,
  }))
);

const PropertiesPage = lazy(() =>
  import("../pages/landlord/PropertiesPage").then((module) => ({
    default: module.PropertiesPage,
  }))
);

const RoomsPage = lazy(() =>
  import("../pages/landlord/RoomsPage").then((module) => ({
    default: module.RoomsPage,
  }))
);

const CaretakersPage = lazy(() =>
  import("../pages/landlord/CaretakersPage").then((module) => ({
    default: module.CaretakersPage,
  }))
);

const TenantsPage = lazy(() =>
  import("../pages/landlord/TenantsPage").then((module) => ({
    default: module.TenantsPage,
  }))
);

const ListingsPage = lazy(() =>
  import("../pages/landlord/ListingsPage").then((module) => ({
    default: module.ListingsPage,
  }))
);

const LeasesPage = lazy(() =>
  import("../pages/landlord/LeasesPage").then((module) => ({
    default: module.LeasesPage,
  }))
);

const RoomRequestsPage = lazy(() =>
  import("../pages/landlord/RoomRequestsPage").then((module) => ({
    default: module.RoomRequestsPage,
  }))
);

const PaymentSubmissionsPage = lazy(() =>
  import("../pages/landlord/PaymentSubmissionsPage").then((module) => ({
    default: module.PaymentSubmissionsPage,
  }))
);

const BillingPage = lazy(() =>
  import("../pages/landlord/BillingPage").then((module) => ({
    default: module.BillingPage,
  }))
);

const SupportTicketsPage = lazy(() =>
  import("../pages/landlord/SupportTicketsPage").then((module) => ({
    default: module.SupportTicketsPage,
  }))
);

const TenantPortalPage = lazy(() =>
  import("../pages/tenant/TenantPortalPage").then((module) => ({
    default: module.TenantPortalPage,
  }))
);

const AdminDashboardPage = lazy(() =>
  import("../pages/admin/AdminDashboardPage").then((module) => ({
    default: module.AdminDashboardPage,
  }))
);

const LandlordRequestsPage = lazy(() =>
  import("../pages/admin/LandlordRequestsPage").then((module) => ({
    default: module.LandlordRequestsPage,
  }))
);

const LandlordVerificationReviewPage = lazy(() =>
  import("../pages/admin/LandlordVerificationReviewPage").then((module) => ({
    default: module.LandlordVerificationReviewPage,
  }))
);

function HomeRedirect() {
  const { user, loading } = useAuth();

  if (loading) {
    return <main className="center-page">Loading Rentalink...</main>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role === "tenant") {
    return <Navigate to="/tenant" replace />;
  }

  if (user.role === "national_admin") {
    return <Navigate to="/admin" replace />;
  }

  if (user.role === "district_admin") {
    return <Navigate to="/district" replace />;
  }

  return <Navigate to="/landlord" replace />;
}

export function AppRoutes() {
  return (
    <Suspense fallback={<main className="center-page">Loading Rentalink...</main>}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/rooms" element={<PublicRoomFinderPage />} />
        <Route path="/apply/:token" element={<ApplicationFormPage />} />
        <Route path="/landlord-request" element={<LandlordRequestPage />} />
        <Route path="/landlord-verification" element={<LandlordVerificationPage />} />
        <Route path="/" element={<HomeRedirect />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/change-password" element={<ChangePasswordPage />} />

          <Route element={<AppLayout />}>
            <Route path="/security" element={<SecurityPage />} />

            <Route element={<ProtectedRoute roles={["national_admin"]} />}>
              <Route path="/admin" element={<AdminDashboardPage section="onboarding" />} />
              <Route path="/admin/requests" element={<AdminDashboardPage section="requests" />} />
              <Route path="/admin/risk" element={<AdminDashboardPage section="risk" />} />
              <Route path="/admin/gateway" element={<AdminDashboardPage section="gateway" />} />
              <Route path="/admin/reminders" element={<AdminDashboardPage section="reminders" />} />
              <Route path="/admin/verification" element={<AdminDashboardPage section="verification" />} />
              <Route path="/admin/plans" element={<AdminDashboardPage section="plans" />} />
              <Route path="/admin/districts" element={<AdminDashboardPage section="districts" />} />
              <Route path="/admin/district-admins" element={<AdminDashboardPage section="district-admins" />} />
              <Route path="/admin/landlords" element={<AdminDashboardPage section="landlords" />} />
              <Route path="/admin/landlord-requests" element={<LandlordRequestsPage />} />
              <Route path="/admin/landlord-verifications" element={<LandlordVerificationReviewPage />} />
            </Route>

            <Route element={<ProtectedRoute roles={["district_admin"]} />}>
              <Route path="/district" element={<AdminDashboardPage section="districts" />} />
              <Route path="/district/landlords" element={<AdminDashboardPage section="landlords" />} />
              <Route path="/district/requests" element={<AdminDashboardPage section="requests" />} />
              <Route path="/district/risk" element={<AdminDashboardPage section="risk" />} />
            </Route>

            <Route
              element={
                <ProtectedRoute
                  roles={[
                    "landlord",
                    "caretaker",
                    "district_admin",
                    "national_admin",
                  ]}
                />
              }
            >
              <Route path="/landlord" element={<LandlordDashboardPage />} />
              <Route path="/landlord/rooms" element={<RoomsPage />} />
              <Route path="/landlord/tenants" element={<TenantsPage />} />
              <Route path="/landlord/listings" element={<ListingsPage />} />
              <Route path="/landlord/leases" element={<LeasesPage />} />
              <Route path="/landlord/requests" element={<RoomRequestsPage />} />
              <Route path="/landlord/payments" element={<PaymentSubmissionsPage />} />
              <Route path="/landlord/support" element={<SupportTicketsPage />} />
            </Route>

            <Route
              element={
                <ProtectedRoute
                  roles={["landlord", "district_admin", "national_admin"]}
                />
              }
            >
              <Route path="/landlord/properties" element={<PropertiesPage />} />
              <Route path="/landlord/caretakers" element={<CaretakersPage />} />
              <Route path="/landlord/billing" element={<BillingPage />} />
            </Route>

            <Route element={<ProtectedRoute roles={["tenant"]} />}>
              <Route path="/tenant" element={<TenantPortalPage section="overview" />} />
              <Route path="/tenant/reminders" element={<TenantPortalPage section="reminders" />} />
              <Route path="/tenant/leases" element={<TenantPortalPage section="leases" />} />
              <Route path="/tenant/rent-dues" element={<TenantPortalPage section="rent-dues" />} />
              <Route path="/tenant/occupancy" element={<TenantPortalPage section="occupancy" />} />
              <Route path="/tenant/payments" element={<TenantPortalPage section="payments" />} />
              <Route path="/tenant/receipts" element={<TenantPortalPage section="receipts" />} />
              <Route path="/tenant/support" element={<TenantPortalPage section="support" />} />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
