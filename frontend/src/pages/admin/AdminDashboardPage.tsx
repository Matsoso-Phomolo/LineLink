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

type DistrictStatus = "active" | "locked";

type District = {
  name: string;
  status: DistrictStatus;
  phase: string;
};

export type AdminSection =
  | "onboarding"
  | "requests"
  | "risk"
  | "gateway"
  | "reminders"
  | "verification"
  | "plans"
  | "landlords"
  | "districts";

const initialDistricts: District[] = [
  { name: "Quthing", status: "locked", phase: "Future rollout" },
  { name: "Mohale's Hoek", status: "locked", phase: "Future rollout" },
  { name: "Mafeteng", status: "locked", phase: "Future rollout" },
  { name: "Maseru", status: "active", phase: "Roma village active now" },
  { name: "Berea", status: "locked", phase: "Future rollout" },
  { name: "Leribe", status: "locked", phase: "Future rollout" },
  { name: "Botha-Bothe", status: "locked", phase: "Future rollout" },
  { name: "Thaba-Tseka", status: "locked", phase: "Future rollout" },
  { name: "Mokhotlong", status: "locked", phase: "Future rollout" },
  { name: "Qacha's Nek", status: "locked", phase: "Future rollout" }
];

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

export function AdminDashboardPage({ section = "onboarding" }: { section?: AdminSection }) {
  const [landlords, setLandlords] = useState<Landlord[]>([]);
  const [requests, setRequests] = useState<LandlordRequest[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [riskCenter, setRiskCenter] = useState<any>(null);
  const [reminderLogs, setReminderLogs] = useState<any[]>([]);
  const [paymentHealth, setPaymentHealth] = useState<any>(null);
  const [districts, setDistricts] = useState<District[]>(initialDistricts);

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

  function toggleDistrict(name: string) {
    setDistricts((current) =>
      current.map((district) =>
        district.name === name
          ? {
              ...district,
              status: district.status === "active" ? "locked" : "active",
              phase: district.status === "active" ? "Future rollout" : "Activated by admin"
            }
          : district
      )
    );
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
      const result = (await apiFetch(`/landlords/requests/${request.id}/${action}`, {
        method: "POST",
        body: JSON.stringify({
          admin_note: action === "approve" ? "Approved by admin." : "Rejected by admin."
        })
      })) as { temporary_password?: string | null };

      setNotice(
        action === "approve" && result.temporary_password
          ? `Landlord approved. Temporary password: ${result.temporary_password}`
          : `Request ${action}d.`
      );

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
        body: JSON.stringify({
          landlord_note:
            action === "verify"
              ? "Listing verified by platform admin."
              : "Listing needs more verification before public visibility."
        })
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
      const result = (await apiFetch("/admin/run-reminders", { method: "POST" })) as {
        tenant_rent_reminders_generated: number;
        subscription_reminders_generated: number;
        skipped_duplicates: number;
      };

      setNotice(
        `Reminders generated: rent ${result.tenant_rent_reminders_generated}, subscriptions ${result.subscription_reminders_generated}, skipped duplicates ${result.skipped_duplicates}.`
      );

      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not run reminders");
    } finally {
      setBusyId("");
    }
  }

  const activeDistricts = districts.filter((district) => district.status === "active").length;
  const lockedDistricts = districts.filter((district) => district.status === "locked").length;

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>{adminSectionTitle(section)}</h1>
          <p>{adminSectionDescription(section)}</p>
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
          {section === "onboarding" ? (
            <div className="admin-grid single-admin-grid">
              <form className="panel form-panel" onSubmit={submitManual}>
                <div>
                  <p className="eyebrow">Manual onboarding</p>
                  <h2>Add landlord</h2>
                </div>

                <label>
                  Business name
                  <input required value={manual.business_name} onChange={(event) => updateManual("business_name", event.target.value)} />
                </label>

                <label>
                  Owner full name
                  <input required value={manual.full_name} onChange={(event) => updateManual("full_name", event.target.value)} />
                </label>

                <div className="form-grid">
                  <label>
                    Email
                    <input required type="email" value={manual.email} onChange={(event) => updateManual("email", event.target.value)} />
                  </label>

                  <label>
                    Phone
                    <input value={manual.phone} onChange={(event) => updateManual("phone", event.target.value)} />
                  </label>
                </div>

                <label>
                  Address
                  <input value={manual.address} onChange={(event) => updateManual("address", event.target.value)} />
                </label>

                <label>
                  Temporary password
                  <input required minLength={8} type="password" value={manual.password} onChange={(event) => updateManual("password", event.target.value)} />
                </label>

                <button className="primary-button" type="submit">
                  Create landlord
                </button>
              </form>
            </div>
          ) : null}

          {section === "requests" ? (
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
                      <button type="button" disabled={busyId === request.id || request.status !== "pending"} onClick={() => decideRequest(request, "approve")}>
                        Approve
                      </button>

                      <button type="button" disabled={busyId === request.id || request.status !== "pending"} onClick={() => decideRequest(request, "reject")}>
                        Reject
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          ) : null}

          {section === "risk" ? (
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
                {(riskCenter?.landlord_risk_cards ?? []).slice(0, 8).map((card: any) => (
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
          ) : null}

          {section === "gateway" ? (
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">MoPay readiness</p>
                  <h2>Payment gateway health</h2>
                </div>

                <StatusPill value={paymentHealth?.mopay_environment ?? "sandbox"} />
              </div>

              <div className="detail-grid compact">
                <div>
                  <span>Webhook URL</span>
                  <strong>{paymentHealth?.webhook_url ?? "Not set"}</strong>
                </div>

                <div>
                  <span>Callback URL</span>
                  <strong>{paymentHealth?.callback_url ?? "Not set"}</strong>
                </div>

                <div>
                  <span>Last webhook</span>
                  <strong>
                    {paymentHealth?.last_webhook_received
                      ? new Date(paymentHealth.last_webhook_received).toLocaleString()
                      : "None yet"}
                  </strong>
                </div>

                <div>
                  <span>Successful payments</span>
                  <strong>{paymentHealth?.successful_payment_count ?? 0}</strong>
                </div>

                <div>
                  <span>Failed webhooks</span>
                  <strong>{paymentHealth?.failed_webhook_count ?? 0}</strong>
                </div>
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
          ) : null}

          {section === "reminders" ? (
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Automation scaffold</p>
                  <h2>Payment reminders</h2>
                </div>

                <button type="button" disabled={busyId === "run-reminders"} onClick={runReminders}>
                  Run reminders
                </button>
              </div>

              <div className="list-stack compact-list">
                {reminderLogs.length === 0 ? <div className="data-state">No reminder logs yet.</div> : null}

                {reminderLogs.slice(0, 20).map((log) => (
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
          ) : null}

          {section === "verification" ? (
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Anti-scam controls</p>
                  <h2>Listing verification</h2>
                </div>
              </div>

              <div className="list-stack compact-list">
                {listings.length === 0 ? <div className="data-state">No listings have been submitted for verification yet.</div> : null}

                {listings.slice(0, 20).map((listing) => (
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
                      <button type="button" disabled={busyId === listing.id} onClick={() => decideListing(listing, "verify")}>
                        Verify
                      </button>

                      <button type="button" disabled={busyId === listing.id} onClick={() => decideListing(listing, "reject-verification")}>
                        Reject
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          ) : null}

          {section === "plans" ? (
            <form className="panel form-panel" onSubmit={savePlan}>
              <div>
                <p className="eyebrow">SaaS monetization</p>
                <h2>Add subscription plan</h2>
              </div>

              <label>
                Plan name
                <input required value={planForm.name} onChange={(event) => setPlanForm((current) => ({ ...current, name: event.target.value }))} />
              </label>

              <div className="form-grid">
                <label>
                  Monthly price
                  <input required inputMode="numeric" value={planForm.monthly_price} onChange={(event) => setPlanForm((current) => ({ ...current, monthly_price: event.target.value }))} />
                </label>

                <label>
                  Max properties
                  <input required inputMode="numeric" value={planForm.max_properties} onChange={(event) => setPlanForm((current) => ({ ...current, max_properties: event.target.value }))} />
                </label>
              </div>

              <label>
                Max rooms
                <input required inputMode="numeric" value={planForm.max_rooms} onChange={(event) => setPlanForm((current) => ({ ...current, max_rooms: event.target.value }))} />
              </label>

              <label>
                Features
                <textarea value={planForm.features} onChange={(event) => setPlanForm((current) => ({ ...current, features: event.target.value }))} />
              </label>

              <button className="primary-button" type="submit">
                Create plan
              </button>

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
          ) : null}

          {section === "districts" ? (
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">National rollout</p>
                  <h2>District access control</h2>
                </div>
              </div>

              <p>
                RentaLink is currently available in Roma village under Maseru district.
                Admin will later activate full Maseru district access, then selected
                districts, and finally all 10 districts of Lesotho.
              </p>

              <div className="metric-grid compact-metrics">
                <Metric label="Current area" value={activeDistricts} />
                <Metric label="Active districts" value={activeDistricts} />
                <Metric label="Locked districts" value={lockedDistricts} />
                <Metric label="Total districts" value={districts.length} />
              </div>

              <div className="list-stack compact-list">
                {districts.map((district) => (
                  <article className="row-item" key={district.name}>
                    <div>
                      <strong>{district.name}</strong>
                      <p>{district.phase}</p>
                    </div>

                    <button
                      type="button"
                      className={`status-toggle ${district.status}`}
                      onClick={() => toggleDistrict(district.name)}
                    >
                      {district.status === "active" ? "Active" : "Locked"}
                    </button>
                  </article>
                ))}
              </div>

              <div className="data-state">
                District activation is currently frontend-controlled. Backend persistence
                and Room Finder district filtering will be connected later.
              </div>
            </div>
          ) : null}

          {section === "landlords" ? (
            <div className="list-stack">
              {landlords.length === 0 ? <div className="data-state">No landlords yet.</div> : null}

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
                    <button type="button" disabled={busyId === landlord.id || !landlord.is_active} onClick={() => disableLandlord(landlord)}>
                      Disable
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : null}
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

function adminSectionTitle(section: AdminSection) {
  const titles: Record<AdminSection, string> = {
    onboarding: "Landlord onboarding",
    requests: "Landlord requests",
    risk: "AI Risk Center",
    gateway: "Payment gateway health",
    reminders: "Payment reminders",
    verification: "Listing verification",
    plans: "Subscription plans",
    landlords: "Landlords",
    districts: "Districts"
  };

  return titles[section];
}

function adminSectionDescription(section: AdminSection) {
  const descriptions: Record<AdminSection, string> = {
    onboarding: "Create landlord accounts manually and issue temporary credentials.",
    requests: "Approve or reject landlord applications submitted from the public request form.",
    risk: "Review automated risk signals, suspicious activity, and admin decision-support indicators.",
    gateway: "Monitor payment gateway readiness, webhook status, and missing production configuration.",
    reminders: "Generate and review automated rent and subscription reminder logs.",
    verification: "Verify or reject listings before they become trusted public room records.",
    plans: "Create and manage SaaS subscription plans for landlords.",
    landlords: "View active landlords and disable accounts when necessary.",
    districts: "Control rollout from Roma village, to Maseru district, then all 10 districts of Lesotho."
  };

  return descriptions[section];
}
