import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

const API_BASE =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:9000";

export default function TenantFinancialDashboard() {
  const { tenantId } = useParams();

  const [summary, setSummary] = useState<any>(null);
  const [balance, setBalance] = useState<any>(null);
  const [history, setHistory] = useState<any>(null);
  const [risk, setRisk] = useState<any>(null);
  const [collection, setCollection] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, [tenantId]);

  async function loadDashboard() {
    if (!tenantId) {
      setLoading(false);
      return;
    }

    try {
      const [
        summaryRes,
        balanceRes,
        historyRes,
        riskRes,
        collectionRes,
      ] = await Promise.all([
        fetch(`${API_BASE}/tenant-financial/${tenantId}/summary`),
        fetch(`${API_BASE}/tenant-financial/${tenantId}/balance`),
        fetch(`${API_BASE}/tenant-financial/${tenantId}/history`),
        fetch(`${API_BASE}/risk/tenant/${tenantId}`),
        fetch(`${API_BASE}/risk/tenant/${tenantId}/collection-probability`),
      ]);

      setSummary(await summaryRes.json());
      setBalance(await balanceRes.json());
      setHistory(await historyRes.json());
      setRisk(await riskRes.json());
      setCollection(await collectionRes.json());
    } catch (error) {
      console.error("Failed to load tenant financial dashboard", error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        Loading Tenant Financial Intelligence...
      </div>
    );
  }

  if (!tenantId) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        Missing tenant ID.
      </div>
    );
  }

  const receipts = history?.receipts || [];

  return (
    <div className="min-h-screen bg-black text-white p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-cyan-400">
          Tenant Financial Intelligence
        </h1>

        <p className="text-gray-400 mt-2">
          Balance tracking, payment history, risk scoring, and collection
          probability intelligence.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-10">
        <Card
          title="Payment Score"
          value={summary?.payment_score || 0}
          color={scoreColor(summary?.payment_score || 0)}
        />

        <Card
          title="Outstanding Balance"
          value={`M${balance?.outstanding_balance || 0}`}
          color="text-red-400"
        />

        <Card
          title="Overdue Count"
          value={summary?.overdue_count || 0}
          color="text-yellow-400"
        />

        <Card
          title="Collection Probability"
          value={`${collection?.collection_probability || 0}%`}
          color="text-green-400"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-10">
        <section className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
          <h2 className="text-2xl font-semibold mb-6">
            Financial Status
          </h2>

          <InfoRow
            label="Tenant"
            value={summary?.tenant_name || risk?.tenant_name || "Unknown"}
          />

          <InfoRow
            label="Risk Level"
            value={risk?.risk_level || "stable"}
            color={riskTextColor(risk?.risk_level)}
          />

          <InfoRow
            label="Default Risk"
            value={risk?.default_risk || "low"}
            color={riskTextColor(risk?.default_risk)}
          />

          <InfoRow
            label="Max Days Overdue"
            value={summary?.max_days_overdue || 0}
            color="text-yellow-400"
          />

          <InfoRow
            label="Total Due"
            value={`M${balance?.total_due || 0}`}
          />

          <InfoRow
            label="Total Paid"
            value={`M${balance?.total_paid || 0}`}
            color="text-green-400"
          />
        </section>

        <section className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
          <h2 className="text-2xl font-semibold mb-6">
            Recommendation
          </h2>

          <div className="bg-black border border-gray-800 rounded-xl p-5">
            <p className="text-gray-300 leading-relaxed">
              {risk?.recommendation ||
                "No recommendation available yet."}
            </p>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-4">
            <MiniStat
              label="Receipts"
              value={history?.total_receipts || 0}
            />

            <MiniStat
              label="Total Paid"
              value={`M${history?.total_paid || 0}`}
            />
          </div>
        </section>
      </div>

      <section className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
        <h2 className="text-2xl font-semibold mb-6">
          Payment Receipt History
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left border-b border-gray-700">
                <th className="pb-3">Receipt Number</th>
                <th className="pb-3">Amount</th>
                <th className="pb-3">Method</th>
                <th className="pb-3">Transaction Ref</th>
                <th className="pb-3">Issued At</th>
              </tr>
            </thead>

            <tbody>
              {receipts.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="py-6 text-gray-400 text-center"
                  >
                    No payment receipts found.
                  </td>
                </tr>
              ) : (
                receipts.map((receipt: any) => (
                  <tr
                    key={receipt.id || receipt.receipt_number}
                    className="border-b border-gray-800"
                  >
                    <td className="py-4 text-cyan-400">
                      {receipt.receipt_number}
                    </td>

                    <td className="py-4 text-green-400">
                      M{receipt.amount}
                    </td>

                    <td className="py-4">
                      {receipt.method}
                    </td>

                    <td className="py-4 text-gray-300">
                      {receipt.transaction_reference || "—"}
                    </td>

                    <td className="py-4 text-gray-400">
                      {formatDate(receipt.issued_at)}
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

function InfoRow({
  label,
  value,
  color = "text-white",
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="flex items-center justify-between border-b border-gray-800 py-3">
      <span className="text-gray-400">{label}</span>
      <span className={`font-semibold ${color}`}>{value}</span>
    </div>
  );
}

function MiniStat({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="bg-black border border-gray-800 rounded-xl p-4">
      <p className="text-gray-400 text-sm mb-2">{label}</p>
      <h3 className="text-2xl font-bold text-cyan-400">{value}</h3>
    </div>
  );
}

function riskTextColor(risk?: string) {
  if (risk === "critical") return "text-red-400";
  if (risk === "risky" || risk === "high") return "text-orange-400";
  if (risk === "watchlist" || risk === "medium") return "text-yellow-400";
  return "text-green-400";
}

function scoreColor(score: number) {
  if (score < 40) return "text-red-400";
  if (score < 60) return "text-orange-400";
  if (score < 80) return "text-yellow-400";
  return "text-green-400";
}

function formatDate(value?: string) {
  if (!value) return "—";

  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}
