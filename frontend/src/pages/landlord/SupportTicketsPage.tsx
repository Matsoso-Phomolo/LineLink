import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { SupportTicket } from "../../types";

export function SupportTicketsPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/support")
      .then(setTickets)
      .catch(() => setTickets([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Support</p>
          <h1>Tenant tickets</h1>
          <p>Maintenance, complaints, and service requests from tenants.</p>
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      <div className="list-stack">
        {!loading && tickets.length === 0 ? (
          <div className="data-state">Tenant support tickets will appear here.</div>
        ) : null}

        {tickets.map((ticket) => (
          <article className="row-item rich" key={ticket.id}>
            <div>
              <div className="card-topline">
                <StatusPill value={ticket.status} />
                <span>{ticket.priority ?? "normal"}</span>
              </div>
              <strong>{ticket.title}</strong>
              <p>{ticket.description}</p>
            </div>
            <span>{ticket.category}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
