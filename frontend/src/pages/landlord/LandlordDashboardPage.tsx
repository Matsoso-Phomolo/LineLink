import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import type { DashboardSummary, NotificationItem } from "../../types";

export function LandlordDashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([apiFetch("/dashboard/summary"), apiFetch("/notifications")])
      .then(([dashboard, notes]) => {
        setSummary(dashboard);
        setNotifications(notes);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load dashboard"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Landlord dashboard</p>
          <h1>Portfolio snapshot</h1>
          <p>Room availability, payments, listings, and tenant operations in one place.</p>
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {summary ? (
        <>
          <div className="metric-grid">
            <Metric label="Properties" value={summary.properties} />
            <Metric label="Rooms" value={summary.rooms} />
            <Metric label="Vacant" value={summary.vacant_rooms} />
            <Metric label="Occupied" value={summary.occupied_rooms} />
            <Metric label="Unpaid dues" value={summary.unpaid_rent_dues} />
            <Metric label="Pending payments" value={summary.pending_payment_submissions} />
            <Metric label="Public listings" value={summary.published_listings} />
            <Metric label="Applications" value={summary.pending_applications} />
            <Metric label="Room requests" value={summary.pending_room_requests} />
            <Metric label="Overdue rent" value={summary.overdue_rent_dues} />
            <Metric label="Maintenance" value={summary.maintenance_tickets} />
            <Metric label="Tenants" value={summary.total_tenants} />
          </div>
          <section className="panel">
            <h2>Recent notifications</h2>
            <div className="list-stack">
              {notifications.slice(0, 5).map((note) => (
                <article key={note.id} className="row-item">
                  <div>
                    <strong>{note.title}</strong>
                    <p>{note.body}</p>
                  </div>
                  <span>{note.category}</span>
                </article>
              ))}
            </div>
          </section>
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
