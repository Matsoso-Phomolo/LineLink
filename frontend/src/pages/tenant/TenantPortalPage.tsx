import { FormEvent, useEffect, useRef, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { LeaseAgreement, PaymentReceipt } from "../../types";

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
  receipts: PaymentReceipt[];
  leases: LeaseAgreement[];
  reminder_logs?: Array<{ id: string; reminder_type: string; scheduled_for: string; status: string; message: string }>;
  support_tickets: Array<{ id: string; title: string; category: string; priority?: string; status: string; created_at: string }>;
};

export type TenantPortalSection =
  | "overview"
  | "reminders"
  | "leases"
  | "rent-dues"
  | "occupancy"
  | "payments"
  | "receipts"
  | "support";

export function TenantPortalPage({ section = "overview" }: { section?: TenantPortalSection }) {
  const [portal, setPortal] = useState<TenantPortal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [payingDueId, setPayingDueId] = useState("");
  const [paymentForm, setPaymentForm] = useState({ amount: "", method: "mopay_mpesa", payer_phone: "" });
  const [reminders, setReminders] = useState<TenantPortal["reminder_logs"]>([]);
  const paymentPanelRef = useRef<HTMLFormElement | null>(null);

  async function loadPortal() {
    setLoading(true);
    setError("");
    try {
      const [portalData, reminderData] = await Promise.all([
        apiFetch("/tenant-portal/me") as Promise<TenantPortal>,
        apiFetch("/reminders/mine") as Promise<TenantPortal["reminder_logs"]>
      ]);
      setPortal(portalData);
      setReminders(reminderData ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load tenant portal");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPortal();
  }, []);

  async function signLease(lease: LeaseAgreement) {
    setNotice("");
    try {
      await apiFetch(`/leases/${lease.id}/tenant-sign`, { method: "POST" });
      setNotice("Lease accepted and signed.");
      await loadPortal();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not sign lease");
    }
  }

  function startPayment(due: TenantPortal["rent_dues"][number]) {
    setNotice("");
    setPayingDueId(due.id);
    setPaymentForm({
      amount: String(Math.max(0, Number(due.amount_due) - Number(due.amount_paid))),
      method: "mopay_mpesa",
      payer_phone: portal?.tenant?.phone ?? ""
    });
  }

  useEffect(() => {
    if (payingDueId) {
      window.setTimeout(() => paymentPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    }
  }, [payingDueId]);

  async function initiatePayment(event: FormEvent) {
    event.preventDefault();
    setNotice("");
    try {
      const result = await apiFetch("/payments/initiate", {
        method: "POST",
        body: JSON.stringify({
          rent_due_id: payingDueId,
          amount: Number(paymentForm.amount),
          method: paymentForm.method,
          payer_phone: paymentForm.payer_phone,
          idempotency_key: `${payingDueId}-${paymentForm.method}-${paymentForm.amount}`
        })
      }) as { provider_message?: string | null };
      setNotice(result.provider_message ?? "Payment request sent. Confirm on your phone using your mobile money PIN.");
      setPayingDueId("");
      await loadPortal();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not initiate payment");
    }
  }

  const sectionTitle: Record<TenantPortalSection, string> = {
    overview: portal?.tenant?.full_name ?? "My rental",
    reminders: "Rent reminders",
    leases: "Lease agreements",
    "rent-dues": "Rent dues",
    occupancy: "Occupancy",
    payments: "Payment history",
    receipts: "Receipts",
    support: "Support tickets"
  };

  const sectionDescription: Record<TenantPortalSection, string> = {
    overview: "A focused summary of your rental account, balance, deposit, and profile status.",
    reminders: "Rent due and overdue reminders sent through Rentalink.",
    leases: "Issued lease agreements and electronic signing status.",
    "rent-dues": "Monthly dues, unpaid balances, and mobile money payment requests.",
    occupancy: "Your active room assignment and occupancy status.",
    payments: "Submitted and processed rent payment history.",
    receipts: "Receipts generated after approved payments.",
    support: "Support and maintenance tickets linked to your tenancy."
  };

  const renderEmpty = (message: string) => <div className="data-state">{message}</div>;

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Tenant portal</p>
          <h1>{sectionTitle[section]}</h1>
          <p>{sectionDescription[section]}</p>
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}
      {portal?.tenant ? (
        <>
          {section === "overview" ? (
            <div className="metric-grid">
              <Metric label="Verification" value={portal.tenant.verification_status.replaceAll("_", " ")} />
              <Metric label="Tenant status" value={(portal.tenant.tenant_status ?? "active").replaceAll("_", " ")} />
              <Metric label="Balance" value={`M${Number(portal.tenant.outstanding_balance ?? 0).toLocaleString()}`} />
              <Metric label="Deposit" value={portal.tenant.deposit_paid ? "Paid" : "Pending"} />
              <Metric label="Student number" value={portal.tenant.student_number ?? "Not set"} />
              <Metric label="Institution" value={portal.tenant.institution ?? "Not set"} />
            </div>
          ) : null}

          {section === "reminders" ? <section className="panel">
            <h2>Rent reminders</h2>
            <div className="list-stack">
              {(reminders ?? []).length === 0 ? renderEmpty("Rent reminders and overdue notices will appear here.") : null}
              {(reminders ?? []).map((reminder) => (
                <article className="row-item" key={reminder.id}>
                  <div>
                    <strong>{reminder.reminder_type.replaceAll("_", " ")}</strong>
                    <p>{reminder.message}</p>
                  </div>
                  <StatusPill value={reminder.status} />
                </article>
              ))}
            </div>
          </section> : null}

          {section === "leases" ? <section className="panel">
            <h2>Lease agreements</h2>
            <div className="list-stack">
              {(portal.leases ?? []).length === 0 ? renderEmpty("No lease agreement has been issued yet.") : null}
              {(portal.leases ?? []).map((lease) => (
                <article className="row-item" key={lease.id}>
                  <div>
                    <strong>{lease.lease_number}</strong>
                    <p>M{Number(lease.monthly_rent).toLocaleString()} monthly from {new Date(lease.start_date).toLocaleDateString()}</p>
                    <small>Landlord signed: {lease.landlord_signed_at ? new Date(lease.landlord_signed_at).toLocaleString() : "Pending"}</small>
                  </div>
                  <div className="review-actions">
                    <StatusPill value={lease.status} />
                    <button type="button" disabled={!["issued", "draft"].includes(lease.status) || Boolean(lease.tenant_signed_at)} onClick={() => signLease(lease)}>
                      {lease.tenant_signed_at ? "Signed" : "Accept / sign"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section> : null}

          {section === "rent-dues" ? <section className="panel">
            <h2>Rent dues</h2>
            <div className="list-stack">
              {portal.rent_dues.length === 0 ? renderEmpty("No rent dues have been generated yet.") : null}
              {portal.rent_dues.map((due) => (
                <article className="row-item" key={due.id}>
                  <div>
                    <strong>{new Date(due.due_month).toLocaleDateString(undefined, { month: "long", year: "numeric" })}</strong>
                    <p>M{Number(due.amount_paid).toLocaleString()} paid of M{Number(due.amount_due).toLocaleString()}{due.is_late ? " - late" : ""}</p>
                  </div>
                  <div className="review-actions">
                    <StatusPill value={due.status} />
                    <button type="button" disabled={due.status === "paid"} onClick={() => startPayment(due)}>Pay rent</button>
                  </div>
                </article>
              ))}
            </div>
          </section> : null}

          {section === "rent-dues" && payingDueId ? (
            <form className="panel form-panel payment-request-panel" ref={paymentPanelRef} onSubmit={initiatePayment}>
              <div>
                <p className="eyebrow">Secure mobile money</p>
                <h2>Submit payment request</h2>
                <p>Rentalink never asks for or stores wallet PINs. Confirm only on the official wallet prompt, USSD, or app.</p>
              </div>
              <div className="form-grid">
                <label>Amount<input required inputMode="numeric" value={paymentForm.amount} onChange={(event) => setPaymentForm((current) => ({ ...current, amount: event.target.value }))} /></label>
                <label>Method<select value={paymentForm.method} onChange={(event) => setPaymentForm((current) => ({ ...current, method: event.target.value }))}>
                  <option value="mopay_mpesa">MoPay M-Pesa</option>
                  <option value="mopay_ecocash">MoPay EcoCash</option>
                  <option value="mopay_card">MoPay Card</option>
                  <option value="mpesa">Legacy MPESA scaffold</option>
                  <option value="ecocash">Legacy EcoCash scaffold</option>
                  <option value="bank_transfer">Bank Transfer</option>
                </select></label>
              </div>
              <label>Wallet phone number<input required value={paymentForm.payer_phone} onChange={(event) => setPaymentForm((current) => ({ ...current, payer_phone: event.target.value }))} /></label>
              {paymentForm.method === "bank_transfer" ? <div className="data-state">Bank transfer remains pending verification. Proof upload will be attached in the next payment-proof step.</div> : null}
              <div className="review-actions">
                <button className="primary-button" type="submit">Submit Payment Request</button>
                <button type="button" onClick={() => setPayingDueId("")}>Cancel</button>
              </div>
            </form>
          ) : null}

          {section === "occupancy" ? <section className="panel">
            <h2>Occupancy</h2>
            <div className="list-stack">
              {portal.occupancies.length === 0 ? renderEmpty("No active occupancy has been assigned yet.") : null}
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
          </section> : null}

          {section === "payments" ? <section className="panel">
            <h2>Payment history</h2>
            <div className="list-stack">
              {(portal.payments ?? []).length === 0 ? renderEmpty("No payment history yet.") : null}
              {(portal.payments ?? []).map((payment) => (
                <article className="row-item" key={payment.id}>
                  <div>
                    <strong>M{Number(payment.amount).toLocaleString()} via {payment.method.replaceAll("_", " ")}</strong>
                    <p>{payment.transaction_reference}</p>
                  </div>
                  <StatusPill value={payment.status} />
                </article>
              ))}
            </div>
          </section> : null}

          {section === "receipts" ? <section className="panel">
            <h2>Receipts</h2>
            <div className="list-stack">
              {(portal.receipts ?? []).length === 0 ? renderEmpty("Receipts will appear after approved payments.") : null}
              {(portal.receipts ?? []).map((receipt) => (
                <article className="row-item" key={receipt.id}>
                  <div>
                    <strong>{receipt.receipt_number}</strong>
                    <p>M{Number(receipt.amount).toLocaleString()} via {receipt.method.replaceAll("_", " ")}</p>
                    <small>{receipt.transaction_reference ?? "No reference"} - {new Date(receipt.issued_at).toLocaleDateString()}</small>
                  </div>
                  <StatusPill value="issued" />
                </article>
              ))}
            </div>
          </section> : null}

          {section === "support" ? <section className="panel">
            <h2>Support tickets</h2>
            <div className="list-stack">
              {(portal.support_tickets ?? []).length === 0 ? renderEmpty("No support tickets have been opened yet.") : null}
              {(portal.support_tickets ?? []).map((ticket) => (
                <article className="row-item" key={ticket.id}>
                  <div>
                    <strong>{ticket.title}</strong>
                    <p>{ticket.category} - {ticket.priority ?? "normal"}</p>
                  </div>
                  <StatusPill value={ticket.status} />
                </article>
              ))}
            </div>
          </section> : null}
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
