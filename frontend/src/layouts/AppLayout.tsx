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
  { to: "/security", label: "Security" }
];

const caretakerLinks = [
  { to: "/landlord", label: "Dashboard" },
  { to: "/landlord/rooms", label: "Rooms" },
  { to: "/landlord/tenants", label: "Tenants" },
  { to: "/landlord/listings", label: "Listings" },
  { to: "/landlord/requests", label: "Room Requests" },
  { to: "/landlord/payments", label: "Payments" },
  { to: "/landlord/support", label: "Support" },
  { to: "/security", label: "Security" }
];

const tenantLinks = [{ to: "/tenant", label: "Tenant portal" }, { to: "/security", label: "Security" }];


const adminLinks = [{ to: "/admin", label: "Admin overview" },
                    { to: "/rooms", label: "Room finder" },
                    { to: "/onboarding", label: "Onboarding" },
                    { to: "/requests", label: "Request" },
                    { to: "/ai risk", label: "AI Risk" },
                    { to: "/payment gateway", label: "Payment Gateway" },
                    { to: "/remainders", label: "Remainders" },
                    { to: "/landlords", label: "Landlords" },
                    { to: "/verification", label: "Verification" },
                    { to: "/plans", label: "Plans" },
                    { to: "/security", label: "Security" }];

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const links = user?.role === "tenant" ? tenantLinks : user?.role === "admin" ? adminLinks : user?.role === "caretaker" ? caretakerLinks : landlordLinks;

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
            <NavLink key={link.to} to={link.to} end={link.to === "/landlord" || link.to === "/tenant" || link.to === "/admin"}>
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
