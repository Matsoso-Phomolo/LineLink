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

type District = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  rollout_stage: string;
  description: string | null;
  activated_at: string | null;
  created_at?: string;
  updated_at?: string | null;
};

type DistrictArea = {
  id: string;
  district_id: string;
  name: string;
  slug: string;
  is_active: boolean;
  description: string | null;
  created_at?: string;
  updated_at?: string | null;
};

type AreaForm = {
  district_id: string;
  name: string;
  description: string;
};

type DistrictAdmin = {
  id: string;
  username?: string | null;
  full_name: string;
  email: string;
  phone?: string | null;
  role: "district_admin";
  is_active: boolean;
  district_id: string;
  district_name: string;
};

type DistrictAdminForm = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  password: string;
  district_id: string;
};

type DistrictView = "districts" | "add-area" | "areas";

export type AdminSection =
  | "onboarding"
  | "requests"
  | "risk"
  | "gateway"
  | "reminders"
  | "verification"
  | "plans"
  | "landlords"
  | "districts"
  | "district-admins";

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

const emptyAreaForm: AreaForm = {
  district_id: "",
  name: "",
  description: ""
};

const emptyDistrictAdminForm: DistrictAdminForm = {
  id: "",
  full_name: "",
  email: "",
  phone: "",
  password: "",
  district_id: ""
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
  const [districts, setDistricts] = useState<District[]>([]);
  const [areas, setAreas] = useState<DistrictArea[]>([]);
  const [districtAdmins, setDistrictAdmins] = useState<DistrictAdmin[]>([]);

  const [manual, setManual] = useState<ManualLandlordForm>(emptyManual);
  const [planForm, setPlanForm] = useState(emptyPlan);
  const [areaForm, setAreaForm] = useState<AreaForm>(emptyAreaForm);
  const [districtAdminForm, setDistrictAdminForm] = useState<DistrictAdminForm>(emptyDistrictAdminForm);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyId, setBusyId] = useState("");
  const [districtView, setDistrictView] = useState<DistrictView>("districts");
  const [selectedDistrictId, setSelectedDistrictId] = useState("all");

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const [landlordItems, requestItems, districtItems, areaItems, districtAdminItems] = await Promise.all([
        apiFetch("/landlords") as Promise<Landlord[]>,
        apiFetch("/landlords/requests") as Promise<LandlordRequest[]>,
        apiFetch("/districts") as Promise<District[]>,
        apiFetch("/district-areas") as Promise<DistrictArea[]>,
        apiFetch("/admin/district-admins") as Promise<DistrictAdmin[]>
      ]);

      setLandlords(landlordItems);
      setRequests(requestItems);
      setDistricts(districtItems);
      setAreas(areaItems);
      setDistrictAdmins(districtAdminItems);

      if (!areaForm.district_id && districtItems.length > 0) {
        setAreaForm((current) => ({ ...current, district_id: districtItems[0].id }));
      }

      if (!districtAdminForm.district_id && districtItems.length > 0) {
        setDistrictAdminForm((current) => ({ ...current, district_id: districtItems[0].id }));
      }

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

  function updateAreaForm<K extends keyof AreaForm>(key: K, value: AreaForm[K]) {
    setAreaForm((current) => ({ ...current, [key]: value }));
  }

  function updateDistrictAdminForm<K extends keyof DistrictAdminForm>(key: K, value: DistrictAdminForm[K]) {
    setDistrictAdminForm((current) => ({ ...current, [key]: value }));
  }

  function editDistrictAdmin(admin: DistrictAdmin) {
    setDistrictAdminForm({
      id: admin.id,
      full_name: admin.full_name,
      email: admin.email,
      phone: admin.phone ?? "",
      password: "",
      district_id: admin.district_id
    });
    setSelectedDistrictId(admin.district_id);
  }

  async function saveDistrictAdmin(event: FormEvent) {
    event.preventDefault();
    setBusyId("district-admin");
    setNotice("");

    try {
      if (districtAdminForm.id) {
        const updatedAdmin = (await apiFetch(`/admin/district-admins/${districtAdminForm.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            full_name: districtAdminForm.full_name,
            email: districtAdminForm.email,
            phone: nullable(districtAdminForm.phone),
            district_id: districtAdminForm.district_id
          })
        })) as DistrictAdmin;

        setDistrictAdmins((current) => current.map((item) => (item.id === updatedAdmin.id ? updatedAdmin : item)));
        setNotice("District admin updated.");
      } else {
        const createdAdmin = (await apiFetch("/admin/district-admins", {
          method: "POST",
          body: JSON.stringify({
            full_name: districtAdminForm.full_name,
            email: districtAdminForm.email,
            phone: nullable(districtAdminForm.phone),
            password: districtAdminForm.password,
            district_id: districtAdminForm.district_id
          })
        })) as DistrictAdmin;

        setDistrictAdmins((current) => [...current, createdAdmin]);
        setNotice(`District admin created. Username: ${createdAdmin.username ?? "created"}`);
      }

      setDistrictAdminForm({
        ...emptyDistrictAdminForm,
        district_id: districtAdminForm.district_id
      });
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not save district admin");
    } finally {
      setBusyId("");
    }
  }

  async function toggleDistrictAdmin(admin: DistrictAdmin) {
    setBusyId(admin.id);
    setNotice("");

    try {
      await apiFetch(`/admin/district-admins/${admin.id}/${admin.is_active ? "disable" : "enable"}`, {
        method: "POST"
      });
      setDistrictAdmins((current) => current.map((item) => item.id === admin.id ? { ...item, is_active: !admin.is_active } : item));
      setNotice(`${admin.full_name} is now ${admin.is_active ? "disabled" : "active"}.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update district admin");
    } finally {
      setBusyId("");
    }
  }

  async function deleteDistrictAdmin(admin: DistrictAdmin) {
    const confirmed = window.confirm(`Delete district admin ${admin.full_name}? This removes their district admin account.`);

    if (!confirmed) {
      return;
    }

    setBusyId(admin.id);
    setNotice("");

    try {
      await apiFetch(`/admin/district-admins/${admin.id}`, { method: "DELETE" });
      setDistrictAdmins((current) => current.filter((item) => item.id !== admin.id));
      setNotice("District admin deleted.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not delete district admin");
    } finally {
      setBusyId("");
    }
  }

  async function toggleDistrict(district: District) {
    setBusyId(district.id);
    setNotice("");

    try {
      const updatedDistrict = (await apiFetch(`/districts/${district.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          is_active: !district.is_active,
          description: district.is_active ? "Future rollout" : "Activated by admin"
        })
      })) as District;

      setDistricts((current) => current.map((item) => (item.id === updatedDistrict.id ? updatedDistrict : item)));
      setNotice(`${updatedDistrict.name} is now ${updatedDistrict.is_active ? "active" : "locked"}.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update district status");
    } finally {
      setBusyId("");
    }
  }

  async function submitArea(event: FormEvent) {
    event.preventDefault();
    setBusyId("add-area");
    setNotice("");

    try {
      const createdArea = (await apiFetch("/district-areas", {
        method: "POST",
        body: JSON.stringify({
          district_id: areaForm.district_id,
          name: areaForm.name,
          description: nullable(areaForm.description),
          is_active: true
        })
      })) as DistrictArea;

      setAreas((current) => [...current, createdArea]);
      setAreaForm((current) => ({ district_id: current.district_id, name: "", description: "" }));
      setDistrictView("areas");
      setNotice(`${createdArea.name} area added successfully.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not add area");
    } finally {
      setBusyId("");
    }
  }

  async function toggleArea(area: DistrictArea) {
    setBusyId(area.id);
    setNotice("");

    try {
      const updatedArea = (await apiFetch(`/district-areas/${area.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          is_active: !area.is_active
        })
      })) as DistrictArea;

      setAreas((current) => current.map((item) => (item.id === updatedArea.id ? updatedArea : item)));
      setNotice(`${updatedArea.name} is now ${updatedArea.is_active ? "active" : "locked"}.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update area");
    } finally {
      setBusyId("");
    }
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

  const activeDistricts = districts.filter((district) => district.is_active).length;
  const lockedDistricts = districts.filter((district) => !district.is_active).length;
  const activeAreas = areas.filter((area) => area.is_active).length;
  const lockedAreas = areas.filter((area) => !area.is_active).length;
  const districtScoped = selectedDistrictId !== "all";
  const selectedDistrict = districts.find((district) => district.id === selectedDistrictId);
  const filteredDistrictAdmins = districtAdmins.filter((admin) => !districtScoped || admin.district_id === selectedDistrictId);
  const filteredRequests = requests.filter((request) => {
    if (!districtScoped) return true;
    const requestProperties = (request as any).properties ?? [];
    return requestProperties.some((property: any) => property.district_id === selectedDistrictId);
  });
  const filteredListings = listings.filter((listing) => !districtScoped || (listing as any).district_id === selectedDistrictId);
  const filteredLandlords = landlords.filter((landlord) => {
    if (!districtScoped) return true;
    return ((landlord as any).district_id === selectedDistrictId || (landlord as any).primary_district_id === selectedDistrictId);
  });
  const showDistrictSelector = section !== "districts" && section !== "gateway";

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1>{adminSectionTitle(section)}</h1>
          <p>{adminSectionDescription(section)}</p>
        </div>

        <div className="header-stat">
          <strong>{districtScoped ? filteredLandlords.length : landlords.length}</strong>
          <span>{districtScoped ? "district landlords" : "landlords"}</span>
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}

      {!loading && !error && showDistrictSelector ? (
        <section className="panel compact-panel district-scope-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">District scope</p>
              <h2>Choose District first</h2>
              <p>
                National Admin actions are filtered by district so requests,
                landlords, listing checks, and district admins remain clearly
                structured.
              </p>
            </div>
          </div>

          <label>
            Active working district
            <select value={selectedDistrictId} onChange={(event) => setSelectedDistrictId(event.target.value)}>
              <option value="all">All districts</option>
              {districts.map((district) => (
                <option key={district.id} value={district.id}>
                  {district.name} {district.is_active ? "" : "(locked)"}
                </option>
              ))}
            </select>
          </label>

          {districtScoped ? (
            <div className="data-state compact-state">
              Showing records for {selectedDistrict?.name ?? "selected district"} only.
            </div>
          ) : (
            <div className="data-state compact-state">
              Choose a district for operational work. Use all districts only for national overview checks.
            </div>
          )}
        </section>
      ) : null}

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
                {filteredRequests.length === 0 ? <div className="data-state">No landlord requests in this district scope.</div> : null}

                {filteredRequests.map((request) => (
                  <article className="application-card" key={request.id}>
                    <div>
                      <div className="card-topline">
                        <StatusPill value={request.status} />
                        <span>{request.email}</span>
                      </div>

                      <strong>{request.business_name}</strong>
                      <p>
                        {request.full_name} - {request.phone ?? "No phone"}
                      </p>
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
                      <p>
                        {card.system_landlord_number ?? "No landlord number"} - score {card.score}
                      </p>
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
                  <strong>{paymentHealth?.last_webhook_received ? new Date(paymentHealth.last_webhook_received).toLocaleString() : "None yet"}</strong>
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
                {filteredListings.length === 0 ? <div className="data-state">No listings have been submitted for verification in this district scope.</div> : null}

                {filteredListings.slice(0, 20).map((listing) => (
                  <article className="application-card" key={listing.id}>
                    <div>
                      <div className="card-topline">
                        <StatusPill value={listing.verification_status ?? (listing.is_verified ? "verified" : "unverified")} />
                        <span>{listing.status}</span>
                      </div>

                      <strong>{listing.title}</strong>
                      <p>
                        {listing.property_name ?? listing.location_area} - {listing.room_number ?? "Room"}
                      </p>
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
                      <p>
                        M{Number(plan.monthly_price).toLocaleString()} monthly - {plan.max_rooms} rooms
                      </p>
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

              <div className="amenities compact admin-subnav">
                <button
                  type="button"
                  className={`chip-button ${districtView === "districts" ? "active" : ""}`}
                  onClick={() => setDistrictView("districts")}
                >
                  Districts
                </button>

                <button
                  type="button"
                  className={`chip-button ${districtView === "add-area" ? "active" : ""}`}
                  onClick={() => setDistrictView("add-area")}
                >
                  Add Area
                </button>

                <button
                  type="button"
                  className={`chip-button ${districtView === "areas" ? "active" : ""}`}
                  onClick={() => setDistrictView("areas")}
                >
                  Areas
                </button>
              </div>

              {districtView === "districts" ? (
                <>
                  <p>
                    RentaLink is currently available in Roma village under Maseru district. Admin will later activate full Maseru district access, then selected districts, and finally all 10 districts of Lesotho.
                  </p>

                  <div className="metric-grid compact-metrics">
                    <Metric label="Active districts" value={activeDistricts} />
                    <Metric label="Locked districts" value={lockedDistricts} />
                    <Metric label="Active areas" value={activeAreas} />
                    <Metric label="Locked areas" value={lockedAreas} />
                  </div>

                  <div className="list-stack compact-list">
                    {districts.map((district) => (
                      <article className="row-item rich" key={district.id}>
                        <div>
                          <div className="card-topline">
                            <StatusPill value={district.is_active ? "active" : "locked"} />
                          </div>

                          <strong>{district.name}</strong>
                          <p>{district.description ?? (district.is_active ? "Activated by admin" : "Future rollout")}</p>
                        </div>

                        <div className="review-actions">
                          <button type="button" className={`status-toggle ${district.is_active ? "active" : "locked"}`} disabled={busyId === district.id} onClick={() => toggleDistrict(district)}>
                            {district.is_active ? "Active" : "Locked"}
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                </>
              ) : null}

              {districtView === "add-area" ? (
                <form className="panel form-panel" onSubmit={submitArea}>
                  <div>
                    <p className="eyebrow">District areas</p>
                    <h2>Add Area</h2>
                  </div>

                  <label>
                    Choose District
                    <select required value={areaForm.district_id} onChange={(event) => updateAreaForm("district_id", event.target.value)}>
                      {districts.map((district) => (
                        <option key={district.id} value={district.id}>
                          {district.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label>
                    Area name
                    <input required placeholder="Example: Roma, Ha-Matala, Lithabaneng" value={areaForm.name} onChange={(event) => updateAreaForm("name", event.target.value)} />
                  </label>

                  <label>
                    Description
                    <textarea placeholder="Optional area description" value={areaForm.description} onChange={(event) => updateAreaForm("description", event.target.value)} />
                  </label>

                  <button className="primary-button" type="submit" disabled={busyId === "add-area"}>
                    {busyId === "add-area" ? "Adding..." : "Add Area"}
                  </button>
                </form>
              ) : null}

              {districtView === "areas" ? (
                <div className="list-stack compact-list">
                  {districts.map((district) => {
                    const districtAreas = areas.filter((area) => area.district_id === district.id);

                    return (
                      <article className="row-item rich" key={district.id}>
                        <div>
                          <div className="card-topline">
                            <StatusPill value={district.is_active ? "active" : "locked"} />
                            <span>{districtAreas.length} areas</span>
                          </div>

                          <strong>{district.name}</strong>

                          <div className="amenities compact">
                            {districtAreas.length === 0 ? <span>No areas yet</span> : null}

                            {districtAreas.map((area) => (
                              <button
                                key={area.id}
                                type="button"
                                className={`status-toggle ${area.is_active ? "active" : "locked"}`}
                                disabled={busyId === area.id}
                                onClick={() => toggleArea(area)}
                              >
                                {area.name}: {area.is_active ? "Active" : "Locked"}
                              </button>
                            ))}
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              ) : null}

              <div className="data-state">
                Districts and areas are backed by the production database. Only the selected district management view is shown here.
              </div>
            </div>
          ) : null}

          {section === "district-admins" ? (
            <div className="admin-grid">
              <form className="panel form-panel" onSubmit={saveDistrictAdmin}>
                <div>
                  <p className="eyebrow">District administration</p>
                  <h2>{districtAdminForm.id ? "Edit District Admin" : "Add District Admin"}</h2>
                  <p>Choose the district first, then create or update the admin responsible for that district.</p>
                </div>

                <label>
                  District
                  <select required value={districtAdminForm.district_id} onChange={(event) => updateDistrictAdminForm("district_id", event.target.value)}>
                    {districts.map((district) => (
                      <option key={district.id} value={district.id}>
                        {district.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Full name
                  <input required value={districtAdminForm.full_name} onChange={(event) => updateDistrictAdminForm("full_name", event.target.value)} />
                </label>

                <label>
                  Email
                  <input required type="email" value={districtAdminForm.email} onChange={(event) => updateDistrictAdminForm("email", event.target.value)} />
                </label>

                <label>
                  Phone
                  <input value={districtAdminForm.phone} onChange={(event) => updateDistrictAdminForm("phone", event.target.value)} />
                </label>

                {!districtAdminForm.id ? (
                  <label>
                    Temporary password
                    <input required minLength={8} type="password" value={districtAdminForm.password} onChange={(event) => updateDistrictAdminForm("password", event.target.value)} />
                  </label>
                ) : null}

                <div className="review-actions">
                  <button className="primary-button" type="submit" disabled={busyId === "district-admin"}>
                    {districtAdminForm.id ? "Save District Admin" : "Create District Admin"}
                  </button>

                  {districtAdminForm.id ? (
                    <button type="button" onClick={() => setDistrictAdminForm({ ...emptyDistrictAdminForm, district_id: selectedDistrictId === "all" ? districts[0]?.id ?? "" : selectedDistrictId })}>
                      Cancel edit
                    </button>
                  ) : null}
                </div>
              </form>

              <div className="panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">District Admins</p>
                    <h2>{districtScoped ? selectedDistrict?.name : "All districts"}</h2>
                  </div>
                </div>

                <div className="list-stack compact-list">
                  {filteredDistrictAdmins.length === 0 ? <div className="data-state">No district admins in this district scope.</div> : null}

                  {filteredDistrictAdmins.map((admin) => (
                    <article className="row-item rich" key={admin.id}>
                      <div>
                        <div className="card-topline">
                          <StatusPill value={admin.is_active ? "active" : "disabled"} />
                          <span>{admin.username ?? "No identifier"}</span>
                        </div>

                        <strong>{admin.full_name}</strong>
                        <p>{admin.email} - {admin.phone ?? "No phone"}</p>
                        <small>{admin.district_name}</small>
                      </div>

                      <div className="review-actions">
                        <button type="button" onClick={() => editDistrictAdmin(admin)}>Edit</button>
                        <button type="button" disabled={busyId === admin.id} onClick={() => toggleDistrictAdmin(admin)}>
                          {admin.is_active ? "Disable" : "Enable"}
                        </button>
                        <button type="button" disabled={busyId === admin.id} onClick={() => deleteDistrictAdmin(admin)}>
                          Delete
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          {section === "landlords" ? (
            <div className="list-stack">
              {filteredLandlords.length === 0 ? <div className="data-state">No landlords in this district scope.</div> : null}

              {filteredLandlords.map((landlord) => (
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
    districts: "Districts",
    "district-admins": "District Admins"
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
    districts: "Control districts, add areas, and manage rollout availability across Lesotho.",
    "district-admins": "Add, edit, disable, or delete District Admins after choosing their operating district."
  };

  return descriptions[section];
}
