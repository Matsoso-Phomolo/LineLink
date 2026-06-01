export type RentalinkRole =
  | "national_admin"
  | "district_admin"
  | "landlord"
  | "caretaker"
  | "tenant";

type DashboardContext = {
  districtId?: string | null;
  tenantId?: string | null;
};

export function getDefaultDashboardForRole(
  role?: string | null,
  context: DashboardContext = {}
): string {
  switch (role) {
    case "national_admin":
      return "/admin/district-admins";

    case "district_admin":
      return context.districtId
        ? `/intelligence/district/${context.districtId}`
        : "/district";

    case "landlord":
      return "/intelligence/portfolio";

    case "caretaker":
      return "/intelligence/alerts";

    case "tenant":
      return context.tenantId
        ? `/intelligence/tenant/${context.tenantId}`
        : "/tenant";

    default:
      return "/login";
  }
}

export function canAccessIntelligence(
  role?: string | null
): boolean {
  return [
    "district_admin",
    "landlord",
    "caretaker",
    "tenant",
  ].includes(role || "");
}
