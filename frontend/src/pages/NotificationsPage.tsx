import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { ErrorState, LoadingState } from "../components/DataState";
import type { NotificationItem } from "../types";

export function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/notifications")
      .then((items) => setNotifications(items as NotificationItem[]))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Could not load notifications")
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="page-stack contained-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Notifications</p>
          <h1>Recent notifications</h1>
          <p>Operational notifications for the selected account appear here only.</p>
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}

      {!loading && !error ? (
        <section className="panel internal-panel">
          <div className="list-stack internal-list">
            {notifications.length === 0 ? (
              <div className="data-state">No notifications yet.</div>
            ) : null}

            {notifications.map((note) => (
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
    </section>
  );
}
