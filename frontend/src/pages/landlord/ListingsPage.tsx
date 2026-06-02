import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { Listing, PropertyItem, Room, TenantApplication } from "../../types";

type ApplicationMap = Record<string, TenantApplication[]>;
type ListingFieldErrors = Partial<Record<keyof ListingForm, string>>;
type GenderPreference = "any" | "male" | "female";

type ListingForm = {
  id?: string;
  property_id: string;
  room_id: string;
  title: string;
  description: string;
  status: Listing["status"];
  is_public: boolean;
  rent_price: string;
  deposit_amount: string;
  room_type: Room["room_type"];
  room_size: string;
  location_area: string;
  allowed_tenant_type: Listing["allowed_tenant_type"];
  available_from: string;
  distance_from_nul: string;
  contact_phone: string;
  water_available: boolean;
  electricity_available: boolean;
  internet_included: boolean;
  furnished: boolean;
  parking_available: boolean;
  pets_allowed: boolean;
  gender_preference: GenderPreference;
  security_features: string;
  house_rules: string;
};

const emptyListing: ListingForm = {
  property_id: "",
  room_id: "",
  title: "",
  description: "",
  status: "published",
  is_public: true,
  rent_price: "",
  deposit_amount: "",
  room_type: "single",
  room_size: "",
  location_area: "",
  allowed_tenant_type: "both",
  available_from: new Date().toISOString().slice(0, 10),
  distance_from_nul: "",
  contact_phone: "",
  water_available: true,
  electricity_available: true,
  internet_included: false,
  furnished: false,
  parking_available: false,
  pets_allowed: false,
  gender_preference: "any",
  security_features: "",
  house_rules: ""
};

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

function nullable(value: string) {
  return value.trim() ? value.trim() : null;
}

function errorLines(message: string) {
  return message.split("\n").map((line) => line.trim()).filter(Boolean);
}

function fieldErrorFromApi(message: string): ListingFieldErrors {
  const errors: ListingFieldErrors = {};
  for (const line of errorLines(message)) {
    const [rawField, ...rest] = line.split(":");
    const field = rawField.trim().split(".").pop() as keyof ListingForm;
    if (field && field in emptyListing && rest.length > 0) {
      errors[field] = rest.join(":").trim();
    }
  }
  return errors;
}

function normalizeGender(value: string | null | undefined): GenderPreference {
  const normalized = (value ?? "any").trim().toLowerCase();
  if (normalized === "male" || normalized === "female") return normalized;
  return "any";
}

function applicationProfileLabel(application: TenantApplication) {
  const category = (application.tenant_category ?? application.tenant_type ?? "other").replace("_", " ");
  const subtype = application.tenant_subtype ? ` / ${application.tenant_subtype.replace("_", " ")}` : "";
  return `${category}${subtype}`;
}

export function ListingsPage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [applications, setApplications] = useState<ApplicationMap>({});
  const [properties, setProperties] = useState<PropertyItem[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [form, setForm] = useState<ListingForm>(emptyListing);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [success, setSuccess] = useState("");
  const [fieldErrors, setFieldErrors] = useState<ListingFieldErrors>({});
  const [busyId, setBusyId] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [listingItems, propertyItems, roomItems] = await Promise.all([
        apiFetch("/listings/mine") as Promise<Listing[]>,
        apiFetch("/properties") as Promise<PropertyItem[]>,
        apiFetch("/rooms") as Promise<Room[]>
      ]);
      setListings(listingItems);
      setProperties(propertyItems);
      setRooms(roomItems);
      setForm((current) => {
        if (current.property_id || propertyItems.length === 0) return current;
        const firstProperty = propertyItems[0];
        const firstRoom = roomItems.find((room) => room.property_id === firstProperty.id && room.status === "vacant");
        return {
          ...current,
          property_id: firstProperty.id,
          room_id: firstRoom?.id ?? "",
          location_area: firstProperty.location_area,
          distance_from_nul: firstProperty.distance_from_nul ?? ""
        };
      });
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
    () => Object.values(applications).flat().filter((application) => ["inquiry_pending", "form_sent", "submitted", "pending", "under_review", "info_requested"].includes(application.status)).length,
    [applications]
  );
  const propertyById = useMemo(() => Object.fromEntries(properties.map((property) => [property.id, property])), [properties]);
  const roomById = useMemo(() => Object.fromEntries(rooms.map((room) => [room.id, room])), [rooms]);
  const listedRoomIds = useMemo(
    () => new Set(listings.filter((listing) => ["draft", "published"].includes(listing.status)).map((listing) => listing.room_id)),
    [listings]
  );
  const availableRooms = useMemo(
    () => rooms.filter((room) => {
      if (form.property_id && room.property_id !== form.property_id) return false;
      if (room.id === form.room_id) return true;
      return room.status === "vacant" && !listedRoomIds.has(room.id);
    }),
    [form.property_id, form.room_id, listedRoomIds, rooms]
  );

  function update<K extends keyof ListingForm>(key: K, value: ListingForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setFieldErrors((current) => ({ ...current, [key]: undefined }));
  }

  function chooseProperty(propertyId: string) {
    const property = propertyById[propertyId];
    const firstRoom = rooms.find((room) => room.property_id === propertyId && room.status === "vacant" && !listedRoomIds.has(room.id));
    setForm((current) => ({
      ...current,
      property_id: propertyId,
      room_id: firstRoom?.id ?? "",
      location_area: property?.location_area ?? "",
      distance_from_nul: property?.distance_from_nul ?? current.distance_from_nul
    }));
  }

  function chooseRoom(roomId: string) {
    const room = roomById[roomId];
    const property = room ? propertyById[room.property_id] : null;
    setForm((current) => ({
      ...current,
      room_id: roomId,
      room_type: room?.room_type ?? current.room_type,
      room_size: room?.room_size ?? current.room_size,
      rent_price: room ? String(room.rent_price) : current.rent_price,
      deposit_amount: room ? String(room.deposit_amount) : current.deposit_amount,
      title: room && property ? `${room.room_number} ${room.room_size ?? ""} ${room.room_type} room in ${property.location_area}`.replace(/\s+/g, " ").trim() : current.title,
      location_area: property?.location_area ?? current.location_area,
      distance_from_nul: property?.distance_from_nul ?? current.distance_from_nul
    }));
  }

  function validateListingForm() {
    const errors: ListingFieldErrors = {};
    if (!form.property_id) errors.property_id = "Property is required.";
    if (!form.room_id) errors.room_id = "Choose a vacant, unlisted room.";
    if (!form.title.trim()) errors.title = "Title is required.";
    if (!form.description.trim()) errors.description = "Description is required.";
    if (!form.location_area.trim()) errors.location_area = "Location area is required.";
    if (!Number.isFinite(Number(form.rent_price)) || Number(form.rent_price) <= 0) {
      errors.rent_price = "Rent must be greater than 0.";
    }
    if (form.deposit_amount && (!Number.isFinite(Number(form.deposit_amount)) || Number(form.deposit_amount) < 0)) {
      errors.deposit_amount = "Deposit cannot be negative.";
    }
    if (form.available_from && Number.isNaN(new Date(form.available_from).getTime())) {
      errors.available_from = "Available from date is invalid.";
    }
    const selectedRoom = roomById[form.room_id];
    if (!form.id && selectedRoom && selectedRoom.status !== "vacant") {
      errors.room_id = `${selectedRoom.room_number} is ${selectedRoom.status.replace("_", " ")}. Only vacant rooms can be listed.`;
    }
    if (!form.id && selectedRoom && listedRoomIds.has(selectedRoom.id)) {
      errors.room_id = `${selectedRoom.room_number} already has an active listing.`;
    }
    return errors;
  }

  async function saveListing(event: FormEvent) {
    event.preventDefault();
    setNotice("");
    setSuccess("");
    const validationErrors = validateListingForm();
    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      setNotice("Fix the highlighted fields before publishing this listing.");
      return;
    }
    const payload = {
      property_id: form.property_id,
      room_id: form.room_id,
      title: form.title,
      description: nullable(form.description),
      rent_price: Number(form.rent_price),
      deposit_amount: Number(form.deposit_amount || 0),
      room_type: form.room_type,
      room_size: nullable(form.room_size),
      location_area: form.location_area,
      allowed_tenant_type: form.allowed_tenant_type,
      available_from: nullable(form.available_from),
      distance_from_nul: nullable(form.distance_from_nul),
      contact_phone: nullable(form.contact_phone),
      water_available: form.water_available,
      electricity_available: form.electricity_available,
      internet_included: form.internet_included,
      furnished: form.furnished,
      parking_available: form.parking_available,
      pets_allowed: form.pets_allowed,
      gender_preference: form.gender_preference,
      security_features: nullable(form.security_features),
      house_rules: nullable(form.house_rules),
      status: form.status,
      is_public: form.is_public
    };
    try {
      if (form.id) {
        await apiFetch(`/listings/${form.id}`, { method: "PUT", body: JSON.stringify(payload) });
        setSuccess("Listing updated.");
      } else {
        await apiFetch("/listings", { method: "POST", body: JSON.stringify(payload) });
        setSuccess("Vacant room published. It appears below immediately and will sync to Room Finder when public and verified.");
      }
      setForm({ ...emptyListing, property_id: properties[0]?.id ?? "" });
      await loadData();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not save listing";
      setFieldErrors(fieldErrorFromApi(message));
      setNotice(message);
    }
  }

  async function updateListingState(listing: Listing, next: { status: Listing["status"]; is_public: boolean }, label: string) {
    setBusyId(listing.id);
    setNotice("");
    setSuccess("");
    try {
      await apiFetch(`/listings/${listing.id}`, {
        method: "PUT",
        body: JSON.stringify({
          status: next.status,
          is_public: next.is_public
        })
      });
      setSuccess(label);
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update listing");
    } finally {
      setBusyId("");
    }
  }

  async function markListingRoomOccupied(listing: Listing) {
    setBusyId(listing.id);
    setNotice("");
    setSuccess("");
    try {
      await apiFetch(`/rooms/${listing.room_id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: "occupied" })
      });
      setSuccess("Room marked occupied. The listing is hidden from public search.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not mark room occupied");
    } finally {
      setBusyId("");
    }
  }

  async function archiveListing(listing: Listing) {
    setBusyId(listing.id);
    setNotice("");
    try {
      await apiFetch(`/listings/${listing.id}`, { method: "DELETE" });
      setNotice("Listing archived and removed from public search.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not archive listing");
    } finally {
      setBusyId("");
    }
  }

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

  function FieldError({ name }: { name: keyof ListingForm }) {
    return fieldErrors[name] ? <span className="form-error">{fieldErrors[name]}</span> : null;
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Marketplace</p>
          <h1>Public room listings</h1>
          <p>Post vacant rooms from your inventory and review applications inside your landlord scope.</p>
        </div>
        <div className="header-stat">
          <strong>{pendingCount}</strong>
          <span>active applications</span>
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {success ? <div className="form-success">{success}</div> : null}
      {notice ? <div className="data-state error">{notice}</div> : null}

      <form className="panel form-panel" onSubmit={saveListing}>
        <div>
          <p className="eyebrow">{form.id ? "Edit listing" : "Post vacant room"}</p>
          <h2>{form.id ? form.title : "Create public listing"}</h2>
        </div>
        <div className="profile-fieldset">
          <h3>Room details</h3>
          <div className="form-grid">
            <label>Property/location<select required value={form.property_id} onChange={(event) => chooseProperty(event.target.value)}>
              <option value="">Choose property</option>
              {properties.map((property) => <option key={property.id} value={property.id}>{property.name} - {property.location_area}</option>)}
            </select><FieldError name="property_id" /></label>
            <label>Vacant room<select required value={form.room_id} onChange={(event) => chooseRoom(event.target.value)}>
              <option value="">Choose vacant room</option>
              {availableRooms.map((room) => (
                <option key={room.id} value={room.id}>
                  {room.room_number} - M{Number(room.rent_price).toLocaleString()} {listedRoomIds.has(room.id) ? "(Listed)" : ""}
                </option>
              ))}
            </select><FieldError name="room_id" /></label>
          </div>
          <label>Title<input required value={form.title} onChange={(event) => update("title", event.target.value)} /><FieldError name="title" /></label>
          <label>Description<textarea required value={form.description} onChange={(event) => update("description", event.target.value)} /><FieldError name="description" /></label>
          <div className="form-grid">
            <label>Location area<input required value={form.location_area} onChange={(event) => update("location_area", event.target.value)} /><FieldError name="location_area" /></label>
            <label>Distance from NUL<input value={form.distance_from_nul} onChange={(event) => update("distance_from_nul", event.target.value)} /></label>
          </div>
          <div className="form-grid">
            <label>Room type<select value={form.room_type} onChange={(event) => update("room_type", event.target.value as Room["room_type"])}>
              <option value="single">Single</option>
              <option value="double">Double</option>
              <option value="multiple">Multiple</option>
            </select></label>
            <label>Room size<select value={form.room_size} onChange={(event) => update("room_size", event.target.value)}>
              <option value="">Not specified</option>
              <option value="small">Small</option>
              <option value="medium">Medium</option>
              <option value="large">Large</option>
            </select></label>
          </div>
        </div>

        <div className="profile-fieldset">
          <h3>Pricing</h3>
          <div className="form-grid">
            <label>Rent<input required inputMode="numeric" value={form.rent_price} onChange={(event) => update("rent_price", event.target.value)} /><FieldError name="rent_price" /></label>
            <label>Deposit<input inputMode="numeric" value={form.deposit_amount} onChange={(event) => update("deposit_amount", event.target.value)} /><FieldError name="deposit_amount" /></label>
          </div>
          <label>Available from<input type="date" value={form.available_from} onChange={(event) => update("available_from", event.target.value)} /><FieldError name="available_from" /></label>
        </div>

        <div className="profile-fieldset">
          <h3>Tenant preferences</h3>
          <div className="form-grid">
            <label>Allowed tenant<select value={form.allowed_tenant_type} onChange={(event) => update("allowed_tenant_type", event.target.value as Listing["allowed_tenant_type"])}>
              <option value="both">Any tenant category</option>
              <option value="student">Students only</option>
              <option value="non_student">Non-students only</option>
            </select></label>
            <label>Gender preference<select value={form.gender_preference} onChange={(event) => update("gender_preference", event.target.value as GenderPreference)}>
              <option value="any">Any</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select><FieldError name="gender_preference" /></label>
          </div>
          <label>Contact phone<input value={form.contact_phone} onChange={(event) => update("contact_phone", event.target.value)} /></label>
        </div>

        <div className="profile-fieldset">
          <h3>Amenities</h3>
          <div className="amenities compact">
            <label className="inline-check"><input type="checkbox" checked={form.water_available} onChange={(event) => update("water_available", event.target.checked)} /> Water</label>
            <label className="inline-check"><input type="checkbox" checked={form.electricity_available} onChange={(event) => update("electricity_available", event.target.checked)} /> Electricity</label>
            <label className="inline-check"><input type="checkbox" checked={form.internet_included} onChange={(event) => update("internet_included", event.target.checked)} /> Internet</label>
            <label className="inline-check"><input type="checkbox" checked={form.furnished} onChange={(event) => update("furnished", event.target.checked)} /> Furnished</label>
            <label className="inline-check"><input type="checkbox" checked={form.parking_available} onChange={(event) => update("parking_available", event.target.checked)} /> Parking</label>
            <label className="inline-check"><input type="checkbox" checked={form.pets_allowed} onChange={(event) => update("pets_allowed", event.target.checked)} /> Pets</label>
          </div>
          <label>Security features<input value={form.security_features} onChange={(event) => update("security_features", event.target.value)} /></label>
          <label>House rules<textarea value={form.house_rules} onChange={(event) => update("house_rules", event.target.value)} /></label>
        </div>

        <div className="profile-fieldset">
          <h3>Publication settings</h3>
          <div className="form-grid">
            <label>Status<select value={form.status} onChange={(event) => update("status", event.target.value as Listing["status"])}>
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="archived">Archived</option>
            </select></label>
            <label className="inline-check"><input type="checkbox" checked={form.is_public} onChange={(event) => update("is_public", event.target.checked)} /> Show publicly when this vacant room is published</label>
          </div>
        </div>
        <div className="review-actions">
          <button className="primary-button" disabled={availableRooms.length === 0 && !form.id} type="submit">{form.id ? "Save listing" : "Post vacant room"}</button>
          {form.id ? <button type="button" onClick={() => setForm({ ...emptyListing, property_id: properties[0]?.id ?? "" })}>Cancel edit</button> : null}
        </div>
      </form>

      <div className="list-stack">
        {listings.map((listing) => (
          <article className="row-item rich listing-review-card" key={listing.id}>
            <div className="listing-review-main">
              <div className="card-topline">
                <StatusPill value={listing.status} />
                <StatusPill value={listing.verification_status ?? (listing.is_verified ? "verified" : "unverified")} />
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
              <div className="review-actions">
                <button type="button" onClick={() => setForm({
                  id: listing.id,
                  property_id: listing.property_id,
                  room_id: listing.room_id,
                  title: listing.title,
                  description: listing.description ?? "",
                  status: listing.status,
                  is_public: listing.is_public,
                  rent_price: String(listing.rent_price),
                  deposit_amount: String(listing.deposit_amount),
                  room_type: listing.room_type,
                  room_size: listing.room_size ?? "",
                  location_area: listing.location_area,
                  allowed_tenant_type: listing.allowed_tenant_type,
                  available_from: listing.available_from ?? new Date().toISOString().slice(0, 10),
                  distance_from_nul: listing.distance_from_nul ?? "",
                  contact_phone: listing.contact_phone ?? "",
                  water_available: listing.water_available,
                  electricity_available: listing.electricity_available,
                  internet_included: listing.internet_included,
                  furnished: listing.furnished,
                  parking_available: listing.parking_available,
                  pets_allowed: listing.pets_allowed,
                  gender_preference: normalizeGender(listing.gender_preference),
                  security_features: listing.security_features ?? "",
                  house_rules: listing.house_rules ?? ""
                })}>Edit listing</button>
                <button type="button" disabled={busyId === listing.id || listing.status === "published"} onClick={() => updateListingState(listing, { status: "published", is_public: true }, "Listing published.")}>Publish</button>
                <button type="button" disabled={busyId === listing.id || listing.status !== "published"} onClick={() => updateListingState(listing, { status: "draft", is_public: false }, "Listing paused and hidden from Room Finder.")}>Pause</button>
                <button type="button" disabled={busyId === listing.id || listing.status === "archived"} onClick={() => archiveListing(listing)}>Unpublish</button>
                <button type="button" disabled={busyId === listing.id || listing.status === "rented"} onClick={() => markListingRoomOccupied(listing)}>Mark occupied</button>
              </div>
              <div className="application-stack">
                {(applications[listing.id] ?? []).length === 0 ? (
                  <div className="data-state">No applications for this listing yet.</div>
                ) : (
                  (applications[listing.id] ?? []).map((application) => {
                    const isRejected = application.status === "rejected";
                    return (
                    <div className="application-card" key={application.id}>
                      <div>
                        <div className="card-topline">
                          <StatusPill value={application.status} />
                          <span>{applicationProfileLabel(application)}</span>
                        </div>
                        <strong>{application.full_name}</strong>
                        <p>{application.phone}{application.email ? ` - ${application.email}` : ""}</p>
                        <p>{application.message}</p>
                        {isRejected ? <p>This rejected request will disappear after 60 minutes.</p> : null}
                        <small>Emergency contact: {application.emergency_contact_name ?? application.emergency_contact ?? "Not provided"}</small>
                      </div>
                      <div className="review-actions">
                        {isRejected ? (
                          <span>Rejected</span>
                        ) : (
                          <>
                            <button type="button" disabled={busyId === application.id} onClick={() => decide(application, "approve")}>Approve</button>
                            <button type="button" disabled={busyId === application.id} onClick={() => decide(application, "request-info")}>Request info</button>
                            <button type="button" disabled={busyId === application.id} onClick={() => decide(application, "reject")}>Reject</button>
                            <button type="button" disabled={busyId === application.id || listing.status === "rented"} onClick={() => assignRoom(listing, application)}>Assign room</button>
                          </>
                        )}
                      </div>
                    </div>
                  );})
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
