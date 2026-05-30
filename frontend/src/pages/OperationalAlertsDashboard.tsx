import { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:9000";

export default function OperationalAlertsDashboard() {
  const [nationalSummary, setNationalSummary] = useState<any>(null);
  const [highRiskDistricts, setHighRiskDistricts] = useState<any[]>([]);
  const [portfolioSummary, setPortfolioSummary] = useState<any>(null);
  const [highRiskTenants, setHighRiskTenants] = useState<any[]>([]);
  const [overdueClusters, setOverdueClusters] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAlerts();
  }, []);

  async function loadAlerts() {
    try {
      const [
        nationalRes,
        districtsRes,
        portfolioRes,
        tenantsRes,
        clustersRes,
      ] = await Promise.all([
        fetch(`${API_BASE}/national-risk/summary`),
        fetch(`${API_BASE}/national-risk/high-risk-districts`),
        fetch(`${API_BASE}/portfolio-risk/summary`),
        fetch(`${API_BASE}/portfolio-risk/high-risk-tenants`),
        fetch(`${API_BASE}/portfolio-risk/overdue-clusters`),
      ]);

      setNationalSummary(await nationalRes.json());
      setHighRiskDistricts(await districtsRes.json());
      setPortfolioSummary(await portfolioRes.json());
      setHighRiskTenants(await tenantsRes.json());
      setOverdueClusters(await clustersRes.json());
    } catch (error) {
      console.error("Failed to load operational alerts", error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        Loading Operational Alerts...
      </div>
    );
  }

  const severeOverdue = overdueClusters?.["30_plus_days"] || 0;
  const criticalTenants = highRiskTenants.filter(
    (tenant: any) => tenant.risk_level === "critical"
  );

  return (
    <div className="min-h-screen bg-black text-white p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-red-400">
          Operational Alerts Center
        </h1>

        <p className="text-gray-400 mt-2">
          SOC-style rental operations monitoring for financial risk, overdue
          concentration, district instability, and critical tenant alerts.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-10">
        <AlertCard
          title="National Risk Level"
          value={nationalSummary?.national_risk_level || "stable"}
          severity={nationalSummary?.national_risk_level || "stable"}
        />

        <AlertCard
          title="High Risk Districts"
          value={highRiskDistricts.length || 0}
          severity={highRiskDistricts.length > 0 ? "risky" : "stable"}
        />

        <AlertCard
          title="Critical Tenants"
          value={criticalTenants.length || 0}
          severity={criticalTenants.length > 0 ? "critical" : "stable"}
        />

        <AlertCard
          title="30+ Days Overdue"
          value={severeOverdue}
          severity={severeOverdue > 0 ? "critical" : "stable"}
        />
      </div>

      <section className="bg-gray-900 rounded-2xl p-6 mb-10 border border-gray-800">
        <h2 className="text-2xl font-semibold mb-6">
          Priority Alert Feed
        </h2>

        <div className="space-y-4">
          {nationalSummary?.national_risk_level !== "stable" && (
            <AlertItem
              severity={nationalSummary?.national_risk_level}
              title="National rental risk deterioration detected"
              description={`National risk level is currently ${nationalSummary?.national_risk_level}. Immediate monitoring is recommended.`}
            />
          )}

          {highRiskDistricts.length > 0 && (
            <AlertItem
              severity="risky"
              title="High-risk districts detected"
              description={`${highRiskDistricts.length} district(s) currently show elevated operational or financial risk.`}
            />
          )}

          {criticalTenants.length > 0 && (
            <AlertItem
              severity="critical"
              title="Critical tenant risk detected"
              description={`${criticalTenants.length} tenant(s) are classified as critical payment/default risk.`}
            />
          )}

          {severeOverdue > 0 && (
            <AlertItem
              severity="critical"
              title="Severe overdue cluster detected"
              description={`${severeOverdue} rent due(s) are overdue by 30+ days.`}
            />
          )}

          {portfolioSummary?.portfolio_risk_level !== "stable" && (
            <AlertItem
              severity={portfolioSummary?.portfolio_risk_level}
              title="Portfolio risk escalation"
              description={`Current landlord portfolio risk level is ${portfolioSummary?.portfolio_risk_level}.`}
            />
          )}

          {nationalSummary?.national_risk_level === "stable" &&
            highRiskDistricts.length === 0 &&
            criticalTenants.length === 0 &&
            severeOverdue === 0 && (
              <div className="bg-black border border-green-700 rounded-xl p-5">
                <p className="text-green-400 font-semibold">
                  No critical operational alerts detected.
                </p>
                <p className="text-gray-400 mt-2">
                  Rentalink intelligence currently shows stable operational
                  conditions.
                </p>
              </div>
            )}
        </div>
      </section>

      <section className="bg-gray-900 rounded-2xl p-6 mb-10 border border-gray-800">
        <h2 className="text-2xl font-semibold mb-6">
          High Risk Districts
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left border-b border-gray-700">
                <th className="pb-3">District</th>
                <th className="pb-3">Collection Health</th>
                <th className="pb-3">Overdue Count</th>
                <th className="pb-3">Exposure</th>
              </tr>
            </thead>

            <tbody>
              {highRiskDistricts.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-gray-400">
                    No high-risk districts detected.
                  </td>
                </tr>
              ) : (
                highRiskDistricts.map((district: any) => (
                  <tr
                    key={district.district_id}
                    className="border-b border-gray-800"
                  >
                    <td className="py-4">{district.district_name}</td>

                    <td className="py-4 text-green-400">
                      {district.district_collection_health}%
                    </td>

                    <td className="py-4 text-yellow-400">
                      {district.overdue_count}
                    </td>

                    <td className="py-4 text-red-400">
                      M{district.overdue_exposure}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
        <h2 className="text-2xl font-semibold mb-6">
          Critical Tenant Watchlist
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left border-b border-gray-700">
                <th className="pb-3">Tenant</th>
                <th className="pb-3">Risk</th>
                <th className="pb-3">Default Risk</th>
                <th className="pb-3">Score</th>
                <th className="pb-3">Collection Probability</th>
                <th className="pb-3">Outstanding</th>
              </tr>
            </thead>

            <tbody>
              {highRiskTenants.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-gray-400">
                    No high-risk tenants detected.
                  </td>
                </tr>
              ) : (
                highRiskTenants.map((tenant: any) => (
                  <tr
                    key={tenant.tenant_id}
                    className="border-b border-gray-800"
                  >
                    <td className="py-4">
                      {tenant.tenant_name || "Unnamed tenant"}
                    </td>

                    <td className={`py-4 ${riskTextColor(tenant.risk_level)}`}>
                      {tenant.risk_level}
                    </td>

                    <td className={`py-4 ${riskTextColor(tenant.default_risk)}`}>
                      {tenant.default_risk}
                    </td>

                    <td className="py-4 text-cyan-400">
                      {tenant.payment_score}
                    </td>

                    <td className="py-4 text-green-400">
                      {tenant.collection_probability}%
                    </td>

                    <td className="py-4 text-red-400">
                      M{tenant.outstanding_balance}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function AlertCard({
  title,
  value,
  severity,
}: {
  title: string;
  value: string | number;
  severity: string;
}) {
  return (
    <div className={`rounded-2xl p-6 border ${severityBorder(severity)} bg-gray-900`}>
      <p className="text-gray-400 text-sm mb-2">{title}</p>
      <h2 className={`text-3xl font-bold ${riskTextColor(severity)}`}>
        {value}
      </h2>
    </div>
  );
}

function AlertItem({
  severity,
  title,
  description,
}: {
  severity: string;
  title: string;
  description: string;
}) {
  return (
    <div className={`bg-black rounded-xl p-5 border ${severityBorder(severity)}`}>
      <div className="flex items-center gap-3 mb-2">
        <span className={`h-3 w-3 rounded-full ${severityDot(severity)}`} />
        <h3 className={`font-semibold ${riskTextColor(severity)}`}>
          {title}
        </h3>
      </div>

      <p className="text-gray-400">{description}</p>
    </div>
  );
}

function riskTextColor(risk?: string) {
  if (risk === "critical") return "text-red-400";
  if (risk === "risky" || risk === "high") return "text-orange-400";
  if (risk === "watchlist" || risk === "medium") return "text-yellow-400";
  return "text-green-400";
}

function severityBorder(severity?: string) {
  if (severity === "critical") return "border-red-700";
  if (severity === "risky" || severity === "high") return "border-orange-700";
  if (severity === "watchlist" || severity === "medium") return "border-yellow-700";
  return "border-green-700";
}

function severityDot(severity?: string) {
  if (severity === "critical") return "bg-red-500";
  if (severity === "risky" || severity === "high") return "bg-orange-500";
  if (severity === "watchlist" || severity === "medium") return "bg-yellow-500";
  return "bg-green-500";
}
