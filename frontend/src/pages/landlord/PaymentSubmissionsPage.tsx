import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { PaymentSubmission } from "../../types";

export function PaymentSubmissionsPage() {
  const [payments, setPayments] = useState<PaymentSubmission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyId, setBusyId] = useState("");

  async function loadData() {
    setLoading(true);
    apiFetch("/payment-submissions")
      .then(setPayments)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load payment submissions"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadData();
  }, []);

  async function decide(payment: PaymentSubmission, action: "approve" | "reject") {
    setBusyId(payment.id);
    setNotice("");
    try {
      await apiFetch(`/payment-submissions/${payment.id}/${action}`, { method: "PUT" });
      setNotice(action === "approve" ? "Payment approved and receipt generated." : "Payment rejected.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update payment");
    } finally {
      setBusyId("");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Payments</p>
          <h1>Payment submissions</h1>
          <p>Review tenant payment proofs and transaction references.</p>
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}
      <div className="table-panel">
        <table>
          <thead>
            <tr>
              <th>Reference</th>
              <th>Method</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Submitted</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((payment) => (
              <tr key={payment.id}>
                <td>{payment.transaction_reference}</td>
                <td>{payment.method}</td>
                <td>M{Number(payment.amount).toLocaleString()}</td>
                <td><StatusPill value={payment.status} /></td>
                <td>{new Date(payment.created_at).toLocaleDateString()}</td>
                <td>
                  <div className="table-actions">
                    <button disabled={busyId === payment.id || payment.status !== "pending"} type="button" onClick={() => decide(payment, "approve")}>Approve</button>
                    <button disabled={busyId === payment.id || payment.status !== "pending"} type="button" onClick={() => decide(payment, "reject")}>Reject</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
