import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import type { Role } from "../types";

function fallbackPath(role: Role): string {
  if (role === "tenant") return "/tenant";
  if (role === "national_admin") return "/admin";
  if (role === "district_admin") return "/district";
  return "/landlord";
}

export function ProtectedRoute({ roles }: { roles?: Role[] }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <main className="center-page">Loading LineLink...</main>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to={fallbackPath(user.role)} replace />;
  }

  return <Outlet />;
}
