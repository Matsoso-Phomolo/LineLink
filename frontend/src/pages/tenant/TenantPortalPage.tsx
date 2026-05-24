import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";

type TenantPortal = {
  tenant: null | {
    id: string;
    full_name: string;
    phone: string;
    email?: string;
    verification_status: string;
    tenant_status?: string;
    student_number?: string;
    institution?: string;
    outstanding_balance?: number;
    deposit_paid?: boolean;
  };
  occupancies: Array<{ id: string; room_id: string; move_in_date: string; monthly_rent: number; deposit_amount: number; status: string }>;
  rent_dues: Array<{ id: string; due_month: string; due_date?: string | null; amount_due: number; amount_paid: number; status: string; is_late?: boolean; late_penalty_amount?: number }>;
  payments: Array<{ id: string; amount: number; method: string; transaction_reference: string; status: string; created_at: string }>;
  support_tickets: Array<{ id: string; title: string; category: string; priority?: string; status: string; created_at: string }>;
};

export function TenantPortalPage() {
  const [portal, setPortal] = useState<TenantPortal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/tenant-portal/me")
      .then(setPortal)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load tenant portal"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Tenant portal</p>
          <h1>{portal?.tenant?.full_name ?? "My rental"}</h1>
          <p>Rent status, occupancy information, payments, and support tickets.</p>
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {portal?.tenant ? (
        <>
          <div className="metric-grid">
            <Metric label="Verification" value={portal.tenant.verification_status.replaceAll("_", " ")} />
            <Metric label="Tenant status" value={(portal.tenant.tenant_status ?? "active").replaceAll("_", " ")} />
            <Metric label="Balance" value={`M${Number(portal.tenant.outstanding_balance ?? 0).toLocaleString()}`} />
            <Metric label="Deposit" value={portal.tenant.deposit_paid ? "Paid" : "Pending"} />
            <Metric label="Student number" value={portal.tenant.student_number ?? "Not set"} />
            <Metric label="Institution" value={portal.tenant.institution ?? "Not set"} />
          </div>

          <section className="panel">
            <h2>Rent dues</h2>
            <div className="list-stack">
              {portal.rent_dues.map((due) => (
                <article className="row-item" key={due.id}>
                  <div>
                    <strong>{new Date(due.due_month).toLocaleDateString(undefined, { month: "long", year: "numeric" })}</strong>
                    <p>M{Number(due.amount_paid).toLocaleString()} paid of M{Number(due.amount_due).toLocaleString()}{due.is_late ? " - late" : ""}</p>
                  </div>
                  <StatusPill value={due.status} />
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <h2>Occupancy</h2>
            <div className="list-stack">
              {portal.occupancies.map((occupancy) => (
                <article className="row-item" key={occupancy.id}>
                  <div>
                    <strong>Room assignment</strong>
                    <p>Move-in {new Date(occupancy.move_in_date).toLocaleDateString()} - M{Number(occupancy.monthly_rent).toLocaleString()} monthly</p>
                  </div>
                  <StatusPill value={occupancy.status} />
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <h2>Payment history</h2>
            <div className="list-stack">
              {(portal.payments ?? []).slice(0, 6).map((payment) => (
                <article className="row-item" key={payment.id}>
                  <div>
                    <strong>M{Number(payment.amount).toLocaleString()} via {payment.method.replaceAll("_", " ")}</strong>
                    <p>{payment.transaction_reference}</p>
                  </div>
                  <StatusPill value={payment.status} />
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <h2>Support tickets</h2>
            <div className="list-stack">
              {(portal.support_tickets ?? []).slice(0, 6).map((ticket) => (
                <article className="row-item" key={ticket.id}>
                  <div>
                    <strong>{ticket.title}</strong>
                    <p>{ticket.category} - {ticket.priority ?? "normal"}</p>
                  </div>
                  <StatusPill value={ticket.status} />
                </article>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <article className="metric-card wide">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
