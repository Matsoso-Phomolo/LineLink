import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

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
  { to: "/tenant", label: "Tenant portal" },
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
  { to: "/rooms", label: "Room finder" },
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
          <span>LL</span>

          <div>
            <strong>LineLink</strong>
            <small>Roma rental ops</small>
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

          <button type="button" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </aside>

      <main className="content-area">
        <Outlet />
      </main>
    </div>
  );
}
