import { FormEvent, useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { Landlord, LandlordRequest, Listing, SubscriptionPlan } from "../../types";

type ManualLandlordForm = {
  business_name: string;
  full_name: string;
  email: string;
  phone: string;
  address: string;
  password: string;
};

const emptyManual: ManualLandlordForm = {
  business_name: "",
  full_name: "",
  email: "",
  phone: "",
  address: "",
  password: ""
};

const emptyPlan = {
  name: "",
  monthly_price: "0",
  max_properties: "1",
  max_rooms: "10",
  features: ""
};

function nullable(value: string) {
  return value.trim() ? value.trim() : null;
}

export function AdminDashboardPage() {
  const [landlords, setLandlords] = useState<Landlord[]>([]);
  const [requests, setRequests] = useState<LandlordRequest[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [riskCenter, setRiskCenter] = useState<any>(null);
  const [reminderLogs, setReminderLogs] = useState<any[]>([]);
  const [paymentHealth, setPaymentHealth] = useState<any>(null);
  const [manual, setManual] = useState<ManualLandlordForm>(emptyManual);
  const [planForm, setPlanForm] = useState(emptyPlan);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyId, setBusyId] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [landlordItems, requestItems] = await Promise.all([
        apiFetch("/landlords") as Promise<Landlord[]>,
        apiFetch("/landlords/requests") as Promise<LandlordRequest[]>
      ]);
      setLandlords(landlordItems);
      setRequests(requestItems);
      const [listingItems, planItems] = await Promise.all([
        apiFetch("/listings/mine") as Promise<Listing[]>,
        apiFetch("/subscriptions/plans") as Promise<SubscriptionPlan[]>
      ]);
      setListings(listingItems);
      setPlans(planItems);
      const [riskItems, reminderItems, healthItems] = await Promise.all([
        apiFetch("/admin/ai-risk-center"),
        apiFetch("/reminders/mine") as Promise<any[]>,
        apiFetch("/payments/gateway-health")
      ]);
      setRiskCenter(riskItems);
      setReminderLogs(reminderItems);
      setPaymentHealth(healthItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load admin data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function updateManual<K extends keyof ManualLandlordForm>(key: K, value: ManualLandlordForm[K]) {
    setManual((current) => ({ ...current, [key]: value }));
  }

  async function submitManual(event: FormEvent) {
    event.preventDefault();
    setNotice("");
    try {
      await apiFetch("/landlords/manual", {
        method: "POST",
        body: JSON.stringify({
          business_name: manual.business_name,
          full_name: manual.full_name,
          email: manual.email,
          phone: nullable(manual.phone),
          address: nullable(manual.address),
          password: manual.password
        })
      });
      setManual(emptyManual);
      setNotice("Landlord account created.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not create landlord");
    }
  }

  async function decideRequest(request: LandlordRequest, action: "approve" | "reject") {
    setBusyId(request.id);
    setNotice("");
    try {
      const result = await apiFetch(`/landlords/requests/${request.id}/${action}`, {
        method: "POST",
        body: JSON.stringify({ admin_note: action === "approve" ? "Approved by admin." : "Rejected by admin." })
      }) as { temporary_password?: string | null };
      setNotice(action === "approve" && result.temporary_password ? `Landlord approved. Temporary password: ${result.temporary_password}` : `Request ${action}d.`);
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : `Could not ${action} request`);
    } finally {
      setBusyId("");
    }
  }

  async function disableLandlord(landlord: Landlord) {
    setBusyId(landlord.id);
    setNotice("");
    try {
      await apiFetch(`/landlords/${landlord.id}/disable`, { method: "POST" });
      setNotice("Landlord disabled.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not disable landlord");
    } finally {
      setBusyId("");
    }
  }

  async function decideListing(listing: Listing, action: "verify" | "reject-verification") {
    setBusyId(listing.id);
    setNotice("");
    try {
      await apiFetch(`/listings/${listing.id}/${action}`, {
        method: "PUT",
        body: JSON.stringify({ landlord_note: action === "verify" ? "Listing verified by platform admin." : "Listing needs more verification before public visibility." })
      });
      setNotice(action === "verify" ? "Listing verified." : "Listing rejected for verification.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update listing verification");
    } finally {
      setBusyId("");
    }
  }

  async function savePlan(event: FormEvent) {
    event.preventDefault();
    setNotice("");
    try {
      await apiFetch("/subscriptions/plans", {
        method: "POST",
        body: JSON.stringify({
          name: planForm.name,
          monthly_price: Number(planForm.monthly_price),
          max_properties: Number(planForm.max_properties),
          max_rooms: Number(planForm.max_rooms),
          features: nullable(planForm.features),
          is_active: true
        })
      });
      setPlanForm(emptyPlan);
      setNotice("Subscription plan added.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not save subscription plan");
    }
  }

  async function disablePlan(plan: SubscriptionPlan) {
    setBusyId(plan.id);
    setNotice("");
    try {
      await apiFetch(`/subscriptions/plans/${plan.id}`, { method: "DELETE" });
      setNotice("Subscription plan disabled.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not disable plan");
    } finally {
      setBusyId("");
    }
  }

  async function runReminders() {
    setBusyId("run-reminders");
    setNotice("");
    try {
      const result = await apiFetch("/admin/run-reminders", { method: "POST" }) as {
        tenant_rent_reminders_generated: number;
        subscription_reminders_generated: number;
        skipped_duplicates: number;
      };
      setNotice(`Reminders generated: rent ${result.tenant_rent_reminders_generated}, subscriptions ${result.subscription_reminders_generated}, skipped duplicates ${result.skipped_duplicates}.`);
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not run reminders");
    } finally {
      setBusyId("");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>Landlord onboarding</h1>
          <p>Only platform admins can approve, create, disable, or identify landlords in LineLink.</p>
        </div>
        <div className="header-stat">
          <strong>{landlords.length}</strong>
          <span>landlords</span>
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}

      {!loading && !error ? (
        <>
          <div className="admin-grid">
            <form className="panel form-panel" onSubmit={submitManual}>
              <div>
                <p className="eyebrow">Manual onboarding</p>
                <h2>Add landlord</h2>
              </div>
              <label>Business name<input required value={manual.business_name} onChange={(event) => updateManual("business_name", event.target.value)} /></label>
              <label>Owner full name<input required value={manual.full_name} onChange={(event) => updateManual("full_name", event.target.value)} /></label>
              <div className="form-grid">
                <label>Email<input required type="email" value={manual.email} onChange={(event) => updateManual("email", event.target.value)} /></label>
                <label>Phone<input value={manual.phone} onChange={(event) => updateManual("phone", event.target.value)} /></label>
              </div>
              <label>Address<input value={manual.address} onChange={(event) => updateManual("address", event.target.value)} /></label>
              <label>Temporary password<input required minLength={8} type="password" value={manual.password} onChange={(event) => updateManual("password", event.target.value)} /></label>
              <button className="primary-button" type="submit">Create landlord</button>
            </form>

            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Requests</p>
                  <h2>Landlord requests</h2>
                </div>
              </div>
              <div className="list-stack compact-list">
                {requests.length === 0 ? <div className="data-state">No landlord requests yet.</div> : null}
                {requests.map((request) => (
                  <article className="application-card" key={request.id}>
                    <div>
                      <div className="card-topline">
                        <StatusPill value={request.status} />
                        <span>{request.email}</span>
                      </div>
                      <strong>{request.business_name}</strong>
                      <p>{request.full_name} - {request.phone ?? "No phone"}</p>
                      <p>{request.message}</p>
                    </div>
                    <div className="review-actions">
                      <button type="button" disabled={busyId === request.id || request.status !== "pending"} onClick={() => decideRequest(request, "approve")}>Approve</button>
                      <button type="button" disabled={busyId === request.id || request.status !== "pending"} onClick={() => decideRequest(request, "reject")}>Reject</button>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </div>

          <div className="admin-grid">
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Decision support only</p>
                  <h2>AI Risk Center</h2>
                </div>
              </div>
              <div className="metric-grid compact-metrics">
                <Metric label="Pending requests" value={riskCenter?.daily_admin_summary?.new_landlord_requests ?? 0} />
                <Metric label="Listing checks" value={riskCenter?.daily_admin_summary?.pending_listing_verification ?? 0} />
                <Metric label="Complaints" value={riskCenter?.daily_admin_summary?.unresolved_complaints ?? 0} />
                <Metric label="Payment alerts" value={riskCenter?.suspicious_payment_alerts?.length ?? 0} />
              </div>
              <div className="list-stack compact-list">
                {(riskCenter?.landlord_risk_cards ?? []).slice(0, 3).map((card: any) => (
                  <article className="row-item" key={card.landlord_id}>
                    <div>
                      <strong>{card.name ?? "Landlord"}</strong>
                      <p>{card.system_landlord_number ?? "No landlord number"} - score {card.score}</p>
                    </div>
                    <StatusPill value={card.level} />
                  </article>
                ))}
              </div>
            </div>

            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">MoPay readiness</p>
                  <h2>Payment gateway health</h2>
                </div>
                <StatusPill value={paymentHealth?.mopay_environment ?? "sandbox"} />
              </div>
              <div className="detail-grid compact">
                <div><span>Webhook URL</span><strong>{paymentHealth?.webhook_url ?? "Not set"}</strong></div>
                <div><span>Callback URL</span><strong>{paymentHealth?.callback_url ?? "Not set"}</strong></div>
                <div><span>Last webhook</span><strong>{paymentHealth?.last_webhook_received ? new Date(paymentHealth.last_webhook_received).toLocaleString() : "None yet"}</strong></div>
                <div><span>Successful payments</span><strong>{paymentHealth?.successful_payment_count ?? 0}</strong></div>
                <div><span>Failed webhooks</span><strong>{paymentHealth?.failed_webhook_count ?? 0}</strong></div>
              </div>
              <div className="list-stack compact-list">
                {Object.entries(paymentHealth?.configured ?? {}).map(([key, value]) => (
                  <article className="row-item" key={key}>
                    <strong>{key}</strong>
                    <StatusPill value={value ? "configured" : "missing"} />
                  </article>
                ))}
              </div>
            </div>
          </div>

          <div className="admin-grid">
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Automation scaffold</p>
                  <h2>Payment reminders</h2>
                </div>
                <button type="button" disabled={busyId === "run-reminders"} onClick={runReminders}>Run reminders</button>
              </div>
              <div className="list-stack compact-list">
                {reminderLogs.length === 0 ? <div className="data-state">No reminder logs yet.</div> : null}
                {reminderLogs.slice(0, 5).map((log) => (
                  <article className="row-item" key={log.id}>
                    <div>
                      <strong>{String(log.reminder_type).replaceAll("_", " ")}</strong>
                      <p>{log.message}</p>
                    </div>
                    <StatusPill value={log.status} />
                  </article>
                ))}
              </div>
            </div>
          </div>

          <div className="admin-grid">
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Anti-scam controls</p>
                  <h2>Listing verification</h2>
                </div>
              </div>
              <div className="list-stack compact-list">
                {listings.length === 0 ? <div className="data-state">No listings have been submitted for verification yet.</div> : null}
                {listings.slice(0, 8).map((listing) => (
                  <article className="application-card" key={listing.id}>
                    <div>
                      <div className="card-topline">
                        <StatusPill value={listing.verification_status ?? (listing.is_verified ? "verified" : "unverified")} />
                        <span>{listing.status}</span>
                      </div>
                      <strong>{listing.title}</strong>
                      <p>{listing.property_name ?? listing.location_area} - {listing.room_number ?? "Room"}</p>
                    </div>
                    <div className="review-actions">
                      <button type="button" disabled={busyId === listing.id} onClick={() => decideListing(listing, "verify")}>Verify</button>
                      <button type="button" disabled={busyId === listing.id} onClick={() => decideListing(listing, "reject-verification")}>Reject</button>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <form className="panel form-panel" onSubmit={savePlan}>
              <div>
                <p className="eyebrow">SaaS monetization</p>
                <h2>Add subscription plan</h2>
              </div>
              <label>Plan name<input required value={planForm.name} onChange={(event) => setPlanForm((current) => ({ ...current, name: event.target.value }))} /></label>
              <div className="form-grid">
                <label>Monthly price<input required inputMode="numeric" value={planForm.monthly_price} onChange={(event) => setPlanForm((current) => ({ ...current, monthly_price: event.target.value }))} /></label>
                <label>Max properties<input required inputMode="numeric" value={planForm.max_properties} onChange={(event) => setPlanForm((current) => ({ ...current, max_properties: event.target.value }))} /></label>
              </div>
              <label>Max rooms<input required inputMode="numeric" value={planForm.max_rooms} onChange={(event) => setPlanForm((current) => ({ ...current, max_rooms: event.target.value }))} /></label>
              <label>Features<textarea value={planForm.features} onChange={(event) => setPlanForm((current) => ({ ...current, features: event.target.value }))} /></label>
              <button className="primary-button" type="submit">Create plan</button>
              <div className="list-stack compact-list">
                {plans.map((plan) => (
                  <article className="row-item" key={plan.id}>
                    <div>
                      <strong>{plan.name}</strong>
                      <p>M{Number(plan.monthly_price).toLocaleString()} monthly - {plan.max_rooms} rooms</p>
                    </div>
                    <button type="button" disabled={busyId === plan.id || !plan.is_active} onClick={() => disablePlan(plan)}>
                      {plan.is_active ? "Disable" : "Disabled"}
                    </button>
                  </article>
                ))}
              </div>
            </form>
          </div>

          <div className="list-stack">
            {landlords.map((landlord) => (
              <article className="row-item rich" key={landlord.id}>
                <div>
                  <div className="card-topline">
                    <StatusPill value={landlord.is_active ? "active" : "disabled"} />
                    <span>{landlord.system_landlord_number ?? "No system number"}</span>
                  </div>
                  <strong>{landlord.business_name}</strong>
                  <p>{landlord.address}</p>
                </div>
                <div className="review-actions">
                  <span>{landlord.contact_phone}</span>
                  <button type="button" disabled={busyId === landlord.id || !landlord.is_active} onClick={() => disableLandlord(landlord)}>Disable</button>
                </div>
              </article>
            ))}
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
