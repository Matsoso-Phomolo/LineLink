import { FormEvent, useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { PaymentReceipt, PaymentTransaction, SubscriptionPlan } from "../../types";

type LandlordSubscription = {
  id: string;
  plan_id: string;
  status: string;
  start_date: string;
  renewal_date?: string | null;
};

export function BillingPage() {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [subscriptions, setSubscriptions] = useState<LandlordSubscription[]>([]);
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [receipts, setReceipts] = useState<PaymentReceipt[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [method, setMethod] = useState("mopay_mpesa");
  const [payerPhone, setPayerPhone] = useState("");
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [planItems, subscriptionItems, transactionItems, receiptItems] = await Promise.all([
        apiFetch("/subscriptions/plans") as Promise<SubscriptionPlan[]>,
        apiFetch("/subscriptions/mine") as Promise<LandlordSubscription[]>,
        apiFetch("/payments/transactions") as Promise<PaymentTransaction[]>,
        apiFetch("/payments/receipts") as Promise<PaymentReceipt[]>
      ]);
      setPlans(planItems);
      setSubscriptions(subscriptionItems);
      setTransactions(transactionItems.filter((item) => item.payment_type === "landlord_subscription"));
      setReceipts(receiptItems.filter((item) => item.receipt_type === "landlord_subscription"));
      setSelectedPlanId(subscriptionItems[0]?.plan_id ?? planItems[0]?.id ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load billing");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const currentSubscription = subscriptions[0];
  const currentPlan = plans.find((plan) => plan.id === (currentSubscription?.plan_id ?? selectedPlanId));
  const amountDue = Number(currentPlan?.monthly_price ?? 0);

  async function pay(event: FormEvent) {
    event.preventDefault();
    setNotice("");
    try {
      const result = await apiFetch("/subscriptions/pay", {
        method: "POST",
        body: JSON.stringify({
          subscription_id: currentSubscription?.id ?? null,
          plan_id: currentSubscription ? null : selectedPlanId,
          amount: amountDue,
          method,
          payer_phone: payerPhone || null
        })
      }) as PaymentTransaction;
      setNotice(result.provider_message ?? "Subscription payment request created.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not start subscription payment");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Billing</p>
          <h1>Subscription</h1>
          <p>Pay landlord SaaS subscriptions through MoPay or manual bank transfer. LineLink never asks for wallet PINs.</p>
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}
      {!loading && !error ? (
        <>
          {currentSubscription?.status && currentSubscription.status !== "active" ? (
            <div className="form-error">Subscription is {currentSubscription.status}. Renew to keep landlord operations fully available.</div>
          ) : null}

          <div className="admin-grid">
            <section className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Current plan</p>
                  <h2>{currentPlan?.name ?? "Choose a plan"}</h2>
                </div>
                <StatusPill value={currentSubscription?.status ?? "due"} />
              </div>
              <div className="detail-grid compact">
                <div><span>Renewal date</span><strong>{currentSubscription?.renewal_date ? new Date(currentSubscription.renewal_date).toLocaleDateString() : "Due now"}</strong></div>
                <div><span>Amount due</span><strong>M{amountDue.toLocaleString()}</strong></div>
                <div><span>Max properties</span><strong>{currentPlan?.max_properties ?? "-"}</strong></div>
                <div><span>Max rooms</span><strong>{currentPlan?.max_rooms ?? "-"}</strong></div>
              </div>
            </section>

            <form className="panel form-panel" onSubmit={pay}>
              <div>
                <p className="eyebrow">Pay subscription</p>
                <h2>MoPay checkout</h2>
              </div>
              <label>Plan<select value={selectedPlanId} onChange={(event) => setSelectedPlanId(event.target.value)} disabled={Boolean(currentSubscription)}>
                {plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name} - M{Number(plan.monthly_price).toLocaleString()}</option>)}
              </select></label>
              <label>Method<select value={method} onChange={(event) => setMethod(event.target.value)}>
                <option value="mopay_mpesa">MoPay M-Pesa</option>
                <option value="mopay_ecocash">MoPay EcoCash</option>
                <option value="mopay_card">MoPay Card</option>
                <option value="bank_transfer">Bank transfer/manual proof</option>
              </select></label>
              {method !== "mopay_card" ? <label>Phone number<input value={payerPhone} onChange={(event) => setPayerPhone(event.target.value)} placeholder="+266..." /></label> : null}
              <button className="primary-button" type="submit" disabled={!selectedPlanId || amountDue <= 0}>Pay subscription</button>
            </form>
          </div>

          <section className="panel">
            <h2>Payment status</h2>
            <div className="list-stack">
              {transactions.length === 0 ? <div className="data-state">No subscription payment transactions yet.</div> : null}
              {transactions.slice(0, 8).map((transaction) => (
                <article className="row-item" key={transaction.id}>
                  <div>
                    <strong>{transaction.method.replaceAll("_", " ")} - M{Number(transaction.amount).toLocaleString()}</strong>
                    <p>{transaction.provider_reference ?? transaction.checkout_request_id ?? transaction.idempotency_key}</p>
                  </div>
                  <StatusPill value={transaction.status} />
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <h2>Receipts</h2>
            <div className="list-stack">
              {receipts.length === 0 ? <div className="data-state">Subscription receipts will appear after successful payments.</div> : null}
              {receipts.map((receipt) => (
                <article className="row-item" key={receipt.id}>
                  <div>
                    <strong>{receipt.receipt_number}</strong>
                    <p>M{Number(receipt.amount).toLocaleString()} via {receipt.method.replaceAll("_", " ")}</p>
                  </div>
                  <StatusPill value="issued" />
                </article>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </section>
  );
}
