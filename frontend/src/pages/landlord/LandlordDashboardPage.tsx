import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { ErrorState, LoadingState } from "../../components/DataState";
import type { DashboardSummary } from "../../types";

export function LandlordDashboardPage() {
  const { user } = useAuth();

  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/dashboard/summary")
      .then((dashboard) => setSummary(dashboard))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Could not load dashboard")
      )
      .finally(() => setLoading(false));
  }, []);

  const totalRooms = summary
    ? summary.vacant_rooms +
      summary.occupied_rooms +
      summary.maintenance_tickets
    : 0;

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Rentalink landlord operations</p>
          <h1>Portfolio snapshot</h1>
          <p>
            View approved properties, rooms, payments, tenant activity, and
            operational alerts for {user?.full_name ?? "your landlord account"}.
          </p>
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}

      {!loading && !error && summary ? (
        <>
          <div className="metric-grid">
            <Metric label="Properties" value={summary.properties} />
            <Metric label="Rooms" value={totalRooms} />
            <Metric label="Vacant" value={summary.vacant_rooms} />
            <Metric label="Occupied" value={summary.occupied_rooms} />
            <Metric label="Maintenance" value={summary.maintenance_tickets} />
            <Metric label="Tenants" value={summary.total_tenants} />
            <Metric label="Unpaid dues" value={summary.unpaid_rent_dues} />
            <Metric
              label="Pending payments"
              value={summary.pending_payment_submissions}
            />
            <Metric label="Public listings" value={summary.published_listings} />
            <Metric label="Applications" value={summary.pending_applications} />
            <Metric label="Room requests" value={summary.pending_room_requests} />
            <Metric label="Overdue rent" value={summary.overdue_rent_dues} />
          </div>
        </>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
