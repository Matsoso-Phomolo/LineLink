import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { Listing } from "../../types";

type ApplicationForm = {
  full_name: string;
  phone: string;
  email: string;
  tenant_type: "student" | "non_student";
  student_number: string;
  institution: string;
  occupation: string;
  preferred_move_in_date: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  message: string;
};

type ViewingForm = {
  full_name: string;
  phone: string;
  email: string;
  preferred_date: string;
  message: string;
};

const emptyApplication: ApplicationForm = {
  full_name: "",
  phone: "",
  email: "",
  tenant_type: "student",
  student_number: "",
  institution: "",
  occupation: "",
  preferred_move_in_date: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  message: ""
};

const emptyViewing: ViewingForm = {
  full_name: "",
  phone: "",
  email: "",
  preferred_date: "",
  message: ""
};

function money(value: number) {
  return `M${Number(value).toLocaleString()}`;
}

function roomLabel(listing: Listing) {
  return listing.room_number ?? listing.title.match(/[A-Z]-\d{3}/i)?.[0] ?? listing.title;
}

function toNullable(value: string) {
  return value.trim() ? value.trim() : null;
}

export function PublicRoomFinderPage() {
  const { user, logout } = useAuth();
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedListingId, setSelectedListingId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("all");
  const [size, setSize] = useState("");
  const [maxRent, setMaxRent] = useState("");
  const [application, setApplication] = useState<ApplicationForm>(emptyApplication);
  const [viewing, setViewing] = useState<ViewingForm>(emptyViewing);
  const [formMessage, setFormMessage] = useState("");
  const [submitting, setSubmitting] = useState("");

  useEffect(() => {
    apiFetch("/public/listings")
      .then(setListings)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load listings"))
      .finally(() => setLoading(false));
  }, []);

  const filteredListings = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const rentLimit = maxRent ? Number(maxRent) : null;
    return listings.filter((listing) => {
      const text = `${listing.title} ${listing.property_name ?? ""} ${listing.location_area} ${listing.room_size ?? ""} ${listing.description ?? ""}`.toLowerCase();
      const matchesQuery = !normalized || text.includes(normalized);
      const matchesType = type === "all" || listing.room_type === type;
      const matchesSize = !size || (listing.room_size ?? "").toLowerCase().includes(size.toLowerCase());
      const matchesRent = !rentLimit || Number(listing.rent_price) <= rentLimit;
      return matchesQuery && matchesType && matchesSize && matchesRent;
    });
  }, [listings, maxRent, query, size, type]);

  const selectedListing = listings.find((listing) => listing.id === selectedListingId) ?? null;

  function updateApplication(key: keyof ApplicationForm, value: string) {
    setApplication((current) => ({ ...current, [key]: value }));
  }

  function updateViewing(key: keyof ViewingForm, value: string) {
    setViewing((current) => ({ ...current, [key]: value }));
  }

  async function submitApplication(event: FormEvent) {
    event.preventDefault();
    if (!selectedListing) return;
    setSubmitting("application");
    setFormMessage("");
    const context = [
      application.institution ? `Institution: ${application.institution}` : "",
      application.emergency_contact_phone ? `Emergency contact phone: ${application.emergency_contact_phone}` : "",
      application.message
    ].filter(Boolean).join("\n");
    try {
      await apiFetch(`/public/listings/${selectedListing.id}/applications`, {
        method: "POST",
        body: JSON.stringify({
          full_name: application.full_name,
          phone: application.phone,
          email: toNullable(application.email),
          tenant_type: application.tenant_type,
          student_number: toNullable(application.student_number),
          occupation: toNullable(application.occupation),
          preferred_move_in_date: toNullable(application.preferred_move_in_date),
          emergency_contact: [application.emergency_contact_name, application.emergency_contact_phone].filter(Boolean).join(" - ") || null,
          message: toNullable(context)
        })
      });
      setApplication(emptyApplication);
      setFormMessage("Application submitted. The landlord or caretaker will review it before any tenant account is created.");
    } catch (err) {
      setFormMessage(err instanceof Error ? err.message : "Application could not be submitted");
    } finally {
      setSubmitting("");
    }
  }

  async function submitViewing(event: FormEvent) {
    event.preventDefault();
    if (!selectedListing) return;
    setSubmitting("viewing");
    setFormMessage("");
    try {
      await apiFetch(`/public/listings/${selectedListing.id}/viewing-requests`, {
        method: "POST",
        body: JSON.stringify({
          full_name: viewing.full_name,
          phone: viewing.phone,
          email: toNullable(viewing.email),
          preferred_date: toNullable(viewing.preferred_date),
          message: toNullable(viewing.message)
        })
      });
      setViewing(emptyViewing);
      setFormMessage("Viewing request sent. The landlord will contact you using the details provided.");
    } catch (err) {
      setFormMessage(err instanceof Error ? err.message : "Viewing request could not be submitted");
    } finally {
      setSubmitting("");
    }
  }

  return (
    <section className="page-stack">
      <div className="public-topbar">
        <div className="brand-mark light">
          <span>LL</span>
          <div>
            <strong>LineLink</strong>
            <small>Room finder</small>
          </div>
        </div>
        <div className="public-actions">
          {user ? (
            <>
              <a href={`#/${user.role === "tenant" ? "tenant" : user.role === "admin" ? "admin" : "landlord"}`}>Dashboard</a>
              <button type="button" onClick={logout}>Sign out</button>
            </>
          ) : (
            <a href="#/login">Sign in</a>
          )}
        </div>
      </div>

      <div className="page-header">
        <div>
          <p className="eyebrow">Public room finder</p>
          <h1>{selectedListing ? selectedListing.title : "Find vacant rooms near Roma and NUL"}</h1>
          <p>
            {selectedListing
              ? "Apply or request a viewing for this exact listing. Applications remain pending until the landlord or caretaker approves them."
              : "Browse published vacant rooms, filter by price and room type, then apply under the correct landlord, property, and room listing."}
          </p>
        </div>
        <div className="header-stat">
          <strong>{selectedListing ? money(selectedListing.rent_price) : filteredListings.length}</strong>
          <span>{selectedListing ? "monthly rent" : "vacant rooms"}</span>
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}

      {!loading && !error && !selectedListing ? (
        <>
          <div className="finder-subnav">
            <div className="toolbar wide">
              <input placeholder="Search area, property, room, or description" value={query} onChange={(event) => setQuery(event.target.value)} />
              <select value={type} onChange={(event) => setType(event.target.value)}>
                <option value="all">All room types</option>
                <option value="single">Single</option>
                <option value="double">Double</option>
              </select>
              <input placeholder="Room size" value={size} onChange={(event) => setSize(event.target.value)} />
              <input placeholder="Max rent" inputMode="numeric" value={maxRent} onChange={(event) => setMaxRent(event.target.value)} />
            </div>
          </div>
          {filteredListings.length > 0 ? (
            <div className="listing-grid">
              {filteredListings.map((listing) => (
                <article className="listing-card" key={listing.id}>
                  <div>
                    <div className="card-topline">
                      <StatusPill value="vacant" />
                      <span>{listing.distance_from_nul ?? "Near NUL"}</span>
                    </div>
                    <h2>{roomLabel(listing)} · {listing.room_size} {listing.room_type}</h2>
                    <p>{listing.property_name ?? "Line-house"} · {listing.location_area}</p>
                  </div>
                  <dl className="detail-grid">
                    <div>
                      <dt>Rent</dt>
                      <dd>{money(listing.rent_price)}</dd>
                    </div>
                    <div>
                      <dt>Deposit</dt>
                      <dd>{money(listing.deposit_amount)}</dd>
                    </div>
                    <div>
                      <dt>Tenant</dt>
                      <dd>{listing.allowed_tenant_type.replace("_", " ")}</dd>
                    </div>
                    <div>
                      <dt>Area</dt>
                      <dd>{listing.location_area}</dd>
                    </div>
                  </dl>
                  <footer>
                    <strong>{listing.contact_phone}</strong>
                    <button className="secondary-button" type="button" onClick={() => setSelectedListingId(listing.id)}>
                      View details and apply
                    </button>
                  </footer>
                </article>
              ))}
            </div>
          ) : (
            <div className="data-state">No vacant rooms match those filters.</div>
          )}
        </>
      ) : null}

      {selectedListing ? (
        <div className="listing-detail-layout">
          <article className="panel listing-detail-card">
            <button className="text-button" type="button" onClick={() => { setSelectedListingId(null); setFormMessage(""); }}>
              Back to all rooms
            </button>
            <div className="card-topline">
              <StatusPill value="vacant" />
              <span>{selectedListing.property_name ?? "Line-house"} · {selectedListing.location_area}</span>
            </div>
            <h2>{roomLabel(selectedListing)} · {selectedListing.room_size} {selectedListing.room_type}</h2>
            <p>{selectedListing.description}</p>
            <dl className="detail-grid">
              <div>
                <dt>Monthly rent</dt>
                <dd>{money(selectedListing.rent_price)}</dd>
              </div>
              <div>
                <dt>Deposit</dt>
                <dd>{money(selectedListing.deposit_amount)}</dd>
              </div>
              <div>
                <dt>Distance</dt>
                <dd>{selectedListing.distance_from_nul ?? "Ask landlord"}</dd>
              </div>
              <div>
                <dt>Contact</dt>
                <dd>{selectedListing.contact_phone ?? "Provided after review"}</dd>
              </div>
            </dl>
            <div className="amenities">
              {selectedListing.water_available ? <span>Water available</span> : null}
              {selectedListing.electricity_available ? <span>Electricity available</span> : null}
              {selectedListing.security_features ? <span>{selectedListing.security_features}</span> : null}
              {selectedListing.house_rules ? <span>{selectedListing.house_rules}</span> : null}
            </div>
          </article>

          <form className="panel form-panel" onSubmit={submitApplication}>
            <div>
              <p className="eyebrow">Apply under this listing</p>
              <h2>Register interest</h2>
              <p>Your application is attached to this landlord, property, and room listing.</p>
            </div>
            <label>Full name<input required value={application.full_name} onChange={(event) => updateApplication("full_name", event.target.value)} /></label>
            <label>Phone<input required value={application.phone} onChange={(event) => updateApplication("phone", event.target.value)} /></label>
            <label>Email optional<input type="email" value={application.email} onChange={(event) => updateApplication("email", event.target.value)} /></label>
            <div className="form-grid">
              <label>Tenant type<select value={application.tenant_type} onChange={(event) => updateApplication("tenant_type", event.target.value)}>
                <option value="student">Student</option>
                <option value="non_student">Non-student</option>
              </select></label>
              <label>Preferred move-in<input type="date" value={application.preferred_move_in_date} onChange={(event) => updateApplication("preferred_move_in_date", event.target.value)} /></label>
            </div>
            <div className="form-grid">
              <label>Student number<input value={application.student_number} onChange={(event) => updateApplication("student_number", event.target.value)} /></label>
              <label>Institution<input value={application.institution} onChange={(event) => updateApplication("institution", event.target.value)} /></label>
            </div>
            <label>Occupation<input value={application.occupation} onChange={(event) => updateApplication("occupation", event.target.value)} /></label>
            <div className="form-grid">
              <label>Emergency contact name<input value={application.emergency_contact_name} onChange={(event) => updateApplication("emergency_contact_name", event.target.value)} /></label>
              <label>Emergency contact phone<input value={application.emergency_contact_phone} onChange={(event) => updateApplication("emergency_contact_phone", event.target.value)} /></label>
            </div>
            <label>Message<textarea value={application.message} onChange={(event) => updateApplication("message", event.target.value)} /></label>
            <button className="primary-button" disabled={submitting === "application"} type="submit">
              {submitting === "application" ? "Submitting..." : "Apply for this room"}
            </button>
          </form>

          <form className="panel form-panel" onSubmit={submitViewing}>
            <div>
              <p className="eyebrow">Viewing request</p>
              <h2>Schedule a viewing</h2>
            </div>
            <label>Full name<input required value={viewing.full_name} onChange={(event) => updateViewing("full_name", event.target.value)} /></label>
            <label>Phone<input required value={viewing.phone} onChange={(event) => updateViewing("phone", event.target.value)} /></label>
            <label>Email optional<input type="email" value={viewing.email} onChange={(event) => updateViewing("email", event.target.value)} /></label>
            <label>Preferred date<input type="date" value={viewing.preferred_date} onChange={(event) => updateViewing("preferred_date", event.target.value)} /></label>
            <label>Message<textarea value={viewing.message} onChange={(event) => updateViewing("message", event.target.value)} /></label>
            <button className="secondary-button" disabled={submitting === "viewing"} type="submit">
              {submitting === "viewing" ? "Sending..." : "Request viewing"}
            </button>
            {formMessage ? <div className="data-state">{formMessage}</div> : null}
          </form>
        </div>
      ) : null}
    </section>
  );
}
