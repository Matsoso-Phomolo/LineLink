import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { ErrorState, LoadingState } from "../../components/DataState";
import type { DashboardSummary, NotificationItem } from "../../types";

type SectionKey =
  | "overview"
  | "payments"
  | "tenants"
  | "support"
  | "notifications"
  | "security";

export function LandlordDashboardPage() {
  const { user } = useAuth();

  const [activeSection, setActiveSection] = useState<SectionKey>("overview");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [reminderLogs, setReminderLogs] = useState<
    Array<{
      id: string;
      reminder_type: string;
      status: string;
      message: string;
      property_id?: string | null;
    }>
  >([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiFetch("/dashboard/summary"),
      apiFetch("/notifications"),
      apiFetch("/reminders/mine"),
    ])
      .then(([dashboard, notes, reminderItems]) => {
        setSummary(dashboard);
        setNotifications(notes);
        setReminderLogs(reminderItems as typeof reminderLogs);
      })
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
    <section className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <div className="sidebar-title">
          <p className="eyebrow">Landlord dashboard</p>
          <h2>{user?.full_name ?? "Landlord"}</h2>
        </div>

        <button
          className={activeSection === "overview" ? "active" : ""}
          type="button"
          onClick={() => setActiveSection("overview")}
        >
          Overview
        </button>

        <button
          className={activeSection === "payments" ? "active" : ""}
          type="button"
          onClick={() => setActiveSection("payments")}
        >
          Payments
        </button>

        <button
          className={activeSection === "tenants" ? "active" : ""}
          type="button"
          onClick={() => setActiveSection("tenants")}
        >
          Tenants
        </button>

        <button
          className={activeSection === "support" ? "active" : ""}
          type="button"
          onClick={() => setActiveSection("support")}
        >
          Support
        </button>

        <button
          className={activeSection === "notifications" ? "active" : ""}
          type="button"
          onClick={() => setActiveSection("notifications")}
        >
          Notifications
        </button>

        <button
          className={activeSection === "security" ? "active" : ""}
          type="button"
          onClick={() => setActiveSection("security")}
        >
          Security
        </button>
      </aside>

      <div className="dashboard-content">
        <div className="page-header">
          <div>
            <p className="eyebrow">Rentalink landlord operations</p>
            <h1>Portfolio snapshot</h1>
            <p>
              View approved properties, rooms, payments, tenant activity, and
              operational alerts in one focused workspace.
            </p>
          </div>
        </div>

        {loading ? <LoadingState /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!loading && !error && activeSection === "overview" && summary ? (
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

            <section className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Rent operations</p>
                  <h2>Reminder history</h2>
                </div>
              </div>

              <div className="list-stack">
                {reminderLogs.length === 0 ? (
                  <div className="data-state">
                    No rent or subscription reminders have been logged yet.
                  </div>
                ) : null}

                {reminderLogs.slice(0, 8).map((reminder) => (
                  <article key={reminder.id} className="row-item">
                    <div>
                      <strong>
                        {reminder.reminder_type.replaceAll("_", " ")}
                      </strong>
                      <p>{reminder.message}</p>
                    </div>
                    <span>{reminder.status}</span>
                  </article>
                ))}
              </div>
            </section>
          </>
        ) : null}

        {!loading && !error && activeSection === "payments" ? (
          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Payments</p>
                <h2>Payment operations</h2>
              </div>
            </div>

            <div className="metric-grid">
              <Metric label="Unpaid dues" value={summary?.unpaid_rent_dues ?? 0} />
              <Metric
                label="Pending payments"
                value={summary?.pending_payment_submissions ?? 0}
              />
              <Metric label="Overdue rent" value={summary?.overdue_rent_dues ?? 0} />
            </div>

            <p>
              Payment records, receipts, rent dues, and subscription billing are
              managed from the Payments section.
            </p>
          </section>
        ) : null}

        {!loading && !error && activeSection === "tenants" ? (
          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Tenants</p>
                <h2>Tenant operations</h2>
              </div>
            </div>

            <div className="metric-grid">
              <Metric label="Tenants" value={summary?.total_tenants ?? 0} />
              <Metric label="Applications" value={summary?.pending_applications ?? 0} />
              <Metric label="Room requests" value={summary?.pending_room_requests ?? 0} />
            </div>

            <p>
              Tenant accounts must remain linked to approved rooms. One room can
              only support one active tenant account.
            </p>
          </section>
        ) : null}

        {!loading && !error && activeSection === "support" ? (
          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Support</p>
                <h2>Support and maintenance</h2>
              </div>
            </div>

            <div className="metric-grid">
              <Metric label="Maintenance" value={summary?.maintenance_tickets ?? 0} />
            </div>

            <p>
              Support tickets, room issues, and maintenance workflows are handled
              here without changing the approved property or room structure.
            </p>
          </section>
        ) : null}

        {!loading && !error && activeSection === "notifications" ? (
          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Notifications</p>
                <h2>Recent notifications</h2>
              </div>
            </div>

            <div className="list-stack">
              {notifications.length === 0 ? (
                <div className="data-state">No notifications yet.</div>
              ) : null}

              {notifications.slice(0, 10).map((note) => (
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
        ) : null}

        {!loading && !error && activeSection === "security" ? (
          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Security</p>
                <h2>Account security</h2>
              </div>
            </div>

            <p>
              Manage password changes, two-factor authentication, and account
              security settings from the Security section.
            </p>
          </section>
        ) : null}
      </div>
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
