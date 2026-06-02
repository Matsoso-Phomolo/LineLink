import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";

type ReminderLog = {
  id: string;
  reminder_type: string;
  status: string;
  message: string;
  property_id?: string | null;
};

export function LandlordRemindersPage() {
  const [reminderLogs, setReminderLogs] = useState<ReminderLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/reminders/mine")
      .then((items) => setReminderLogs(items as ReminderLog[]))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Could not load reminders")
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="page-stack contained-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Rent operations</p>
          <h1>Reminder history</h1>
          <p>Rent and subscription reminders are displayed separately from the dashboard.</p>
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}

      {!loading && !error ? (
        <section className="panel internal-panel">
          <div className="list-stack internal-list">
            {reminderLogs.length === 0 ? (
              <div className="data-state">
                No rent or subscription reminders have been logged yet.
              </div>
            ) : null}

            {reminderLogs.map((reminder) => (
              <article key={reminder.id} className="row-item">
                <div>
                  <strong>{reminder.reminder_type.replaceAll("_", " ")}</strong>
                  <p>{reminder.message}</p>
                </div>
                <span>{reminder.status}</span>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}
