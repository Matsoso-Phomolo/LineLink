import { Route } from "react-router-dom";

import IntelligenceLayout from "../layouts/IntelligenceLayout";
import DistrictIntelligenceDashboard from "../pages/DistrictIntelligenceDashboard";
import ExecutiveOverviewDashboard from "../pages/ExecutiveOverviewDashboard";
import LandlordPortfolioDashboard from "../pages/LandlordPortfolioDashboard";
import NationalIntelligenceDashboard from "../pages/NationalIntelligenceDashboard";
import OperationalAlertsDashboard from "../pages/OperationalAlertsDashboard";
import TenantFinancialDashboard from "../pages/TenantFinancialDashboard";

export function IntelligenceRoutes() {
  return (
    <Route path="/intelligence" element={<IntelligenceLayout />}>
      <Route index element={<ExecutiveOverviewDashboard />} />

      <Route
        path="national"
        element={<NationalIntelligenceDashboard />}
      />

      <Route
        path="district/:districtId"
        element={<DistrictIntelligenceDashboard />}
      />

      <Route
        path="portfolio"
        element={<LandlordPortfolioDashboard />}
      />

      <Route
        path="tenant/:tenantId"
        element={<TenantFinancialDashboard />}
      />

      <Route
        path="alerts"
        element={<OperationalAlertsDashboard />}
      />
    </Route>
  );
}
