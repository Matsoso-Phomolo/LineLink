import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { InstallAppButton } from "../components/InstallAppButton";
import { PWAPrompt } from "../components/PWAPrompt";

const landlordLinks = [
  { to: "/landlord", label: "Dashboard" },
  { to: "/landlord/properties", label: "Properties" },
  { to: "/landlord/rooms", label: "Rooms" },
  { to: "/landlord/caretakers", label: "Caretakers" },
  { to: "/landlord/tenants", label: "Tenants" },
  { to: "/landlord/listings", label: "Listings" },
  { to: "/landlord/leases", label: "Leases" },
  { to: "/landlord/requests", label: "Room Requests" },
  { to: "/landlord/payments", label: "Payments" },
  { to: "/landlord/billing", label: "Billing" },
  { to: "/landlord/support", label: "Support" },
  { to: "/security", label: "Security" },
];

const caretakerLinks = [
  { to: "/landlord", label: "Dashboard" },
  { to: "/landlord/rooms", label: "Rooms" },
  { to: "/landlord/tenants", label: "Tenants" },
  { to: "/landlord/listings", label: "Listings" },
  { to: "/landlord/requests", label: "Room Requests" },
  { to: "/landlord/payments", label: "Payments" },
  { to: "/landlord/support", label: "Support" },
  { to: "/security", label: "Security" },
];

const tenantLinks = [
  { to: "/tenant", label: "Overview" },
  { to: "/tenant/reminders", label: "Rent reminders" },
  { to: "/tenant/leases", label: "Lease agreements" },
  { to: "/tenant/rent-dues", label: "Rent dues" },
  { to: "/tenant/occupancy", label: "Occupancy" },
  { to: "/tenant/payments", label: "Payment history" },
  { to: "/tenant/receipts", label: "Receipts" },
  { to: "/tenant/support", label: "Support tickets" },
  { to: "/security", label: "Security" },
];

const districtAdminLinks = [
  { to: "/district", label: "District Dashboard" },
  { to: "/district/landlords", label: "District Landlords" },
  { to: "/district/requests", label: "District Requests" },
  { to: "/district/risk", label: "District Risk Center" },
  { to: "/landlord/properties", label: "Properties" },
  { to: "/landlord/rooms", label: "Rooms" },
  { to: "/landlord/tenants", label: "Tenants" },
  { to: "/landlord/listings", label: "Listings" },
  { to: "/landlord/leases", label: "Leases" },
  { to: "/landlord/requests", label: "Room Requests" },
  { to: "/landlord/payments", label: "Payments" },
  { to: "/landlord/support", label: "Support" },
  { to: "/rooms", label: "Room Finder" },
  { to: "/security", label: "Security" },
];

const nationalAdminLinks = [
  { to: "/admin", label: "National Admin Dashboard" },
  { to: "/admin/landlord-requests", label: "Landlord Requests" },
  { to: "/admin/landlord-verifications", label: "Verification Reviews" },
  { to: "/admin/requests", label: "Room Requests" },
  { to: "/admin/risk", label: "AI Risk Center" },
  { to: "/admin/gateway", label: "Payment Gateway" },
  { to: "/admin/reminders", label: "Payment Reminders" },
  { to: "/admin/verification", label: "Listing Verification" },
  { to: "/admin/plans", label: "Subscription Plans" },
  { to: "/admin/districts", label: "Districts" },
  { to: "/admin/district-admins", label: "District Admins" },
  { to: "/admin/landlords", label: "Landlords" },
  { to: "/rooms", label: "Room Finder" },
  { to: "/security", label: "Security" },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const links =
    user?.role === "tenant"
      ? tenantLinks
      : user?.role === "national_admin"
      ? nationalAdminLinks
      : user?.role === "district_admin"
      ? districtAdminLinks
      : user?.role === "caretaker"
      ? caretakerLinks
      : landlordLinks;

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="brand-mark">
          <span>RL</span>

          <div>
            <strong>Rentalink</strong>
            <small>Rental operations</small>
          </div>
        </div>

        <nav className="nav-list">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={
                link.to === "/landlord" ||
                link.to === "/tenant" ||
                link.to === "/admin" ||
                link.to === "/district" ||
                link.to === "/rooms" ||
                link.to === "/security"
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-user">
          <small>{user?.role}</small>
          <strong>{user?.full_name}</strong>
          <span>{user?.username}</span>
          <span>{user?.email}</span>

          <InstallAppButton />

          <button type="button" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </aside>

      <main className="content-area">
        <PWAPrompt />
        <Outlet />
      </main>
    </div>
  );
}
