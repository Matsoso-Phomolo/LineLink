import { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:9000";

export default function NationalIntelligenceDashboard() {
  const [summary, setSummary] = useState<any>(null);
  const [distribution, setDistribution] = useState<any>(null);
  const [overdue, setOverdue] = useState<any>(null);
  const [districts, setDistricts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      const [
        summaryRes,
        distributionRes,
        overdueRes,
        districtsRes,
      ] = await Promise.all([
        fetch(`${API_BASE}/national-risk/summary`),
        fetch(`${API_BASE}/national-risk/distribution`),
        fetch(`${API_BASE}/national-risk/overdue-exposure`),
        fetch(`${API_BASE}/national-risk/high-risk-districts`),
      ]);

      const summaryData = await summaryRes.json();
      const distributionData = await distributionRes.json();
      const overdueData = await overdueRes.json();
      const districtsData = await districtsRes.json();

      setSummary(summaryData);
      setDistribution(distributionData);
      setOverdue(overdueData);
      setDistricts(districtsData);
    } catch (error) {
      console.error("Failed to load national intelligence", error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        Loading National Intelligence...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-cyan-400">
          Rentalink National Intelligence
        </h1>

        <p className="text-gray-400 mt-2">
          AI-Enhanced National Rental Governance &
          Financial Intelligence Infrastructure
        </p>
      </div>

      {/* KPI SECTION */}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-10">
        <Card
          title="National Collection Health"
          value={`${summary?.national_collection_health || 0}%`}
          color="text-green-400"
        />

        <Card
          title="National Risk Level"
          value={summary?.national_risk_level || "stable"}
          color="text-yellow-400"
        />

        <Card
          title="Overdue Exposure"
          value={`M${overdue?.national_overdue_exposure || 0}`}
          color="text-red-400"
        />

        <Card
          title="High Risk Districts"
          value={districts?.length || 0}
          color="text-orange-400"
        />
      </div>

      {/* DISTRIBUTION */}

      <div className="bg-gray-900 rounded-2xl p-6 mb-10 border border-gray-800">
        <h2 className="text-2xl font-semibold mb-6">
          National Risk Distribution
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

      {/* DISTRICT TABLE */}

      <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
        <h2 className="text-2xl font-semibold mb-6">
          High Risk District Intelligence
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
              {districts.map((district: any) => (
                <tr
                  key={district.district_id}
                  className="border-b border-gray-800"
                >
                  <td className="py-4">
                    {district.district_name}
                  </td>

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
              ))}
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

      <h2 className={`text-3xl font-bold ${color}`}>
        {value}
      </h2>
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
      <div
        className={`w-4 h-4 rounded-full ${color} mb-4`}
      />

      <p className="text-gray-400 mb-2">{label}</p>

      <h3 className="text-3xl font-bold">
        {value}
      </h3>
    </div>
  );
}
