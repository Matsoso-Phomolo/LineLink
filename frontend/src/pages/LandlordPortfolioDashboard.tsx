import { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:9000";

export default function LandlordPortfolioDashboard() {
  const [summary, setSummary] = useState<any>(null);
  const [distribution, setDistribution] = useState<any>(null);
  const [collection, setCollection] = useState<any>(null);
  const [clusters, setClusters] = useState<any>(null);
  const [highRiskTenants, setHighRiskTenants] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      const [
        summaryRes,
        distributionRes,
        collectionRes,
        clustersRes,
        tenantsRes,
      ] = await Promise.all([
        fetch(`${API_BASE}/portfolio-risk/summary`),
        fetch(`${API_BASE}/portfolio-risk/distribution`),
        fetch(`${API_BASE}/portfolio-risk/collection-health`),
        fetch(`${API_BASE}/portfolio-risk/overdue-clusters`),
        fetch(`${API_BASE}/portfolio-risk/high-risk-tenants`),
      ]);

      setSummary(await summaryRes.json());
      setDistribution(await distributionRes.json());
      setCollection(await collectionRes.json());
      setClusters(await clustersRes.json());
      setHighRiskTenants(await tenantsRes.json());
    } catch (error) {
      console.error("Failed to load landlord portfolio dashboard", error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        Loading Landlord Portfolio Intelligence...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-cyan-400">
          Landlord Portfolio Intelligence
        </h1>

        <p className="text-gray-400 mt-2">
          Predictive rental risk, collection performance, tenant instability,
          and overdue cluster analytics.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-10">
        <Card
          title="Portfolio Collection Health"
          value={`${collection?.portfolio_collection_health || 0}%`}
          color="text-green-400"
        />

        <Card
          title="Portfolio Risk Level"
          value={summary?.portfolio_risk_level || "stable"}
          color={riskTextColor(summary?.portfolio_risk_level || "stable")}
        />

        <Card
          title="High Risk Tenants"
          value={highRiskTenants.length || 0}
          color="text-orange-400"
        />

        <Card
          title="Total Tenants"
          value={summary?.total_tenants || 0}
          color="text-cyan-400"
        />
      </div>

      <div className="bg-gray-900 rounded-2xl p-6 mb-10 border border-gray-800">
        <h2 className="text-2xl font-semibold mb-6">
          Portfolio Risk Distribution
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <RiskCard
            label="Stable"
            value={distribution?.stable || 0}
            color="bg-green-500"
          />

          <RiskCard
            label="Watchlist"
            value={distribution?.watchlist || 0}
            color="bg-yellow-500"
          />

          <RiskCard
            label="Risky"
            value={distribution?.risky || 0}
            color="bg-orange-500"
          />

          <RiskCard
            label="Critical"
            value={distribution?.critical || 0}
            color="bg-red-500"
          />
        </div>
      </div>

      <div className="bg-gray-900 rounded-2xl p-6 mb-10 border border-gray-800">
        <h2 className="text-2xl font-semibold mb-6">
          Overdue Cluster Analytics
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <RiskCard
            label="1–6 Days"
            value={clusters?.["1_6_days"] || 0}
            color="bg-yellow-400"
          />

          <RiskCard
            label="7–13 Days"
            value={clusters?.["7_13_days"] || 0}
            color="bg-orange-400"
          />

          <RiskCard
            label="14–29 Days"
            value={clusters?.["14_29_days"] || 0}
            color="bg-orange-600"
          />

          <RiskCard
            label="30+ Days"
            value={clusters?.["30_plus_days"] || 0}
            color="bg-red-600"
          />
        </div>
      </div>

      <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
        <h2 className="text-2xl font-semibold mb-6">
          High Risk Tenants
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left border-b border-gray-700">
                <th className="pb-3">Tenant</th>
                <th className="pb-3">Risk Level</th>
                <th className="pb-3">Default Risk</th>
                <th className="pb-3">Payment Score</th>
                <th className="pb-3">Collection Probability</th>
                <th className="pb-3">Overdue Count</th>
                <th className="pb-3">Outstanding Balance</th>
              </tr>
            </thead>

            <tbody>
              {highRiskTenants.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="py-6 text-gray-400 text-center"
                  >
                    No high-risk tenants found.
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

                    <td className="py-4 text-yellow-400">
                      {tenant.overdue_count}
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
      </div>
    </div>
  );
}

function Card({
  title,
  value,
  color,
}: {
  title: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
      <p className="text-gray-400 text-sm mb-2">{title}</p>
      <h2 className={`text-3xl font-bold ${color}`}>{value}</h2>
    </div>
  );
}

function RiskCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="bg-black rounded-xl p-5 border border-gray-800">
      <div className={`w-4 h-4 rounded-full ${color} mb-4`} />
      <p className="text-gray-400 mb-2">{label}</p>
      <h3 className="text-3xl font-bold">{value}</h3>
    </div>
  );
}

function riskTextColor(risk: string) {
  if (risk === "critical") return "text-red-400";
  if (risk === "risky" || risk === "high") return "text-orange-400";
  if (risk === "watchlist" || risk === "medium") return "text-yellow-400";
  return "text-green-400";
}
