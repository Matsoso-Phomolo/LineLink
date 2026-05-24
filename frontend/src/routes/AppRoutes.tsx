import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";
import { ProtectedRoute } from "./ProtectedRoute";
import { LoginPage } from "../pages/LoginPage";
import { ForgotPasswordPage } from "../pages/ForgotPasswordPage";
import { ChangePasswordPage } from "../pages/ChangePasswordPage";
import { PublicRoomFinderPage } from "../pages/public/PublicRoomFinderPage";
import { ApplicationFormPage } from "../pages/public/ApplicationFormPage";
import { LandlordDashboardPage } from "../pages/landlord/LandlordDashboardPage";
import { PropertiesPage } from "../pages/landlord/PropertiesPage";
import { RoomsPage } from "../pages/landlord/RoomsPage";
import { CaretakersPage } from "../pages/landlord/CaretakersPage";
import { TenantsPage } from "../pages/landlord/TenantsPage";
import { ListingsPage } from "../pages/landlord/ListingsPage";
import { LeasesPage } from "../pages/landlord/LeasesPage";
import { RoomRequestsPage } from "../pages/landlord/RoomRequestsPage";
import { PaymentSubmissionsPage } from "../pages/landlord/PaymentSubmissionsPage";
import { SupportTicketsPage } from "../pages/landlord/SupportTicketsPage";
import { TenantPortalPage } from "../pages/tenant/TenantPortalPage";
import { AdminDashboardPage } from "../pages/admin/AdminDashboardPage";
import { useAuth } from "../auth/AuthContext";

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <main className="center-page">Loading LineLink...</main>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "tenant") return <Navigate to="/tenant" replace />;
  if (user.role === "admin") return <Navigate to="/admin" replace />;
  return <Navigate to="/landlord" replace />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/rooms" element={<PublicRoomFinderPage />} />
      <Route path="/apply/:token" element={<ApplicationFormPage />} />
      <Route path="/" element={<HomeRedirect />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/change-password" element={<ChangePasswordPage />} />
        <Route element={<AppLayout />}>
          <Route element={<ProtectedRoute roles={["admin"]} />}>
            <Route path="/admin" element={<AdminDashboardPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={["landlord", "caretaker", "admin"]} />}>
            <Route path="/landlord" element={<LandlordDashboardPage />} />
            <Route path="/landlord/properties" element={<PropertiesPage />} />
            <Route path="/landlord/rooms" element={<RoomsPage />} />
            <Route path="/landlord/caretakers" element={<CaretakersPage />} />
            <Route path="/landlord/tenants" element={<TenantsPage />} />
            <Route path="/landlord/listings" element={<ListingsPage />} />
            <Route path="/landlord/leases" element={<LeasesPage />} />
            <Route path="/landlord/requests" element={<RoomRequestsPage />} />
            <Route path="/landlord/payments" element={<PaymentSubmissionsPage />} />
            <Route path="/landlord/support" element={<SupportTicketsPage />} />
          </Route>
          <Route element={<ProtectedRoute roles={["tenant"]} />}>
            <Route path="/tenant" element={<TenantPortalPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
