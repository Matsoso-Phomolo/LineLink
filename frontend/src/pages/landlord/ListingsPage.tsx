import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { Listing, TenantApplication } from "../../types";

type ApplicationMap = Record<string, TenantApplication[]>;

function money(value: number) {
  return `M${Number(value).toLocaleString()}`;
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function currentMonthStart() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
}

export function ListingsPage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [applications, setApplications] = useState<ApplicationMap>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyId, setBusyId] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const listingItems = await apiFetch("/listings/mine") as Listing[];
      setListings(listingItems);
      const pairs = await Promise.all(
        listingItems.map(async (listing) => {
          const apps = await apiFetch(`/listings/${listing.id}/applications`) as TenantApplication[];
          return [listing.id, apps] as const;
        })
      );
      setApplications(Object.fromEntries(pairs));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load listings");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const pendingCount = useMemo(
    () => Object.values(applications).flat().filter((application) => ["pending", "under_review", "info_requested"].includes(application.status)).length,
    [applications]
  );

  async function decide(application: TenantApplication, action: "approve" | "reject" | "request-info") {
    const note = action === "request-info" ? "Please provide more information before approval." : action === "reject" ? "Application rejected after review." : "Application approved for assignment.";
    setBusyId(application.id);
    setNotice("");
    try {
      await apiFetch(`/applications/${application.id}/${action}`, {
        method: action === "approve" || action === "reject" ? "PUT" : "POST",
        body: JSON.stringify({ landlord_note: note })
      });
      setNotice(`Application ${action.replace("-", " ")} completed.`);
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update application");
    } finally {
      setBusyId("");
    }
  }

  async function assignRoom(listing: Listing, application: TenantApplication) {
    setBusyId(application.id);
    setNotice("");
    try {
      await apiFetch(`/applications/${application.id}/assign-room`, {
        method: "POST",
        body: JSON.stringify({
          move_in_date: application.preferred_move_in_date ?? today(),
          monthly_rent: Number(listing.rent_price),
          deposit_amount: Number(listing.deposit_amount),
          billing_start_month: currentMonthStart(),
          create_invitation_if_no_user: true
        })
      });
      setNotice("Applicant assigned. Occupancy is active, room is occupied, and the public listing is now unavailable.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not assign room");
    } finally {
      setBusyId("");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Marketplace</p>
          <h1>Public room listings</h1>
          <p>Review listing applications inside your landlord scope and convert approved applicants into tenants only after approval.</p>
        </div>
        <div className="header-stat">
          <strong>{pendingCount}</strong>
          <span>active applications</span>
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}
      <div className="list-stack">
        {listings.map((listing) => (
          <article className="row-item rich listing-review-card" key={listing.id}>
            <div className="listing-review-main">
              <div className="card-topline">
                <StatusPill value={listing.status} />
                <span>{listing.is_public ? "public" : "private"}</span>
                <span>{listing.property_name ?? listing.location_area}</span>
              </div>
              <strong>{listing.title}</strong>
              <p>{listing.description}</p>
              <dl className="detail-grid compact">
                <div><dt>Room</dt><dd>{listing.room_number ?? listing.room_id.slice(0, 8)}</dd></div>
                <div><dt>Rent</dt><dd>{money(listing.rent_price)}</dd></div>
                <div><dt>Deposit</dt><dd>{money(listing.deposit_amount)}</dd></div>
                <div><dt>Area</dt><dd>{listing.location_area}</dd></div>
              </dl>
              <div className="application-stack">
                {(applications[listing.id] ?? []).length === 0 ? (
                  <div className="data-state">No applications for this listing yet.</div>
                ) : (
                  (applications[listing.id] ?? []).map((application) => (
                    <div className="application-card" key={application.id}>
                      <div>
                        <div className="card-topline">
                          <StatusPill value={application.status} />
                          <span>{application.tenant_type.replace("_", " ")}</span>
                        </div>
                        <strong>{application.full_name}</strong>
                        <p>{application.phone}{application.email ? ` · ${application.email}` : ""}</p>
                        <p>{application.message}</p>
                        <small>Emergency contact: {application.emergency_contact ?? "Not provided"}</small>
                      </div>
                      <div className="review-actions">
                        <button type="button" disabled={busyId === application.id} onClick={() => decide(application, "approve")}>Approve</button>
                        <button type="button" disabled={busyId === application.id} onClick={() => decide(application, "request-info")}>Request info</button>
                        <button type="button" disabled={busyId === application.id} onClick={() => decide(application, "reject")}>Reject</button>
                        <button type="button" disabled={busyId === application.id || listing.status === "rented"} onClick={() => assignRoom(listing, application)}>Assign room</button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div className="row-money">
              <strong>{money(listing.rent_price)}</strong>
              <span>{listing.location_area}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
