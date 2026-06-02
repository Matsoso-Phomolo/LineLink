import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { Listing, RoomReservation } from "../../types";

type PublicRoomFinderPageProps = {
  returnTo?: string;
  returnLabel?: string;
};

type ApplicationForm = {
  full_name: string;
  phone: string;
  email: string;
  preferred_response_method: "phone_call" | "whatsapp" | "email" | "sms";
  message: string;
};

type District = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  rollout_stage: string;
  description: string | null;
};

type DistrictArea = {
  id: string;
  district_id: string;
  name: string;
  slug: string;
  is_active: boolean;
  description: string | null;
};

const emptyApplication: ApplicationForm = {
  full_name: "",
  phone: "",
  email: "",
  preferred_response_method: "whatsapp",
  message: ""
};

const romaVillages = [
  "Hatabutle",
  "Mafikeng",
  "Thoteng",
  "Ten-House",
  "Liphehleng",
  "Liphakoeng",
  "Ha-Ntja",
  "Keiting",
  "Mangopeng"
];

const responseHelp = {
  phone_call: "The landlord/caretaker will call this number.",
  whatsapp: "A WhatsApp response will be sent to this phone number.",
  email: "A response will be sent to this email address.",
  sms: "An SMS response will be sent to this phone number."
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

export function PublicRoomFinderPage({
  returnTo = "/login",
  returnLabel = "Leave"
}: PublicRoomFinderPageProps = {}) {
  const { user, logout } = useAuth();

  const [listings, setListings] = useState<Listing[]>([]);
  const [districts, setDistricts] = useState<District[]>([]);
  const [areas, setAreas] = useState<DistrictArea[]>([]);

  const [selectedDistrict, setSelectedDistrict] = useState<District | null>(null);
  const [selectedArea, setSelectedArea] = useState<DistrictArea | null>(null);
  const [selectedVillage, setSelectedVillage] = useState("");

  const [loading, setLoading] = useState(true);
  const [loadingAreas, setLoadingAreas] = useState(false);
  const [error, setError] = useState("");
  const [selectedListingId, setSelectedListingId] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [type, setType] = useState("all");
  const [size, setSize] = useState("");
  const [minRent, setMinRent] = useState("");
  const [maxRent, setMaxRent] = useState("");
  const [distance, setDistance] = useState("");
  const [genderPreference, setGenderPreference] = useState<"any" | "male" | "female">("any");
  const [mustHaveWater, setMustHaveWater] = useState(false);
  const [mustHaveElectricity, setMustHaveElectricity] = useState(false);
  const [mustBeFurnished, setMustBeFurnished] = useState(false);

  const [application, setApplication] = useState<ApplicationForm>(emptyApplication);
  const [formMessage, setFormMessage] = useState("");
  const [reservationLink, setReservationLink] = useState("");
  const [submitting, setSubmitting] = useState("");

  useEffect(() => {
    async function loadRoomFinder() {
      setLoading(true);
      setError("");

      try {
        const [listingItems, districtItems] = await Promise.all([
          apiFetch("/public/listings") as Promise<Listing[]>,
          apiFetch("/districts/active") as Promise<District[]>
        ]);

        setListings(listingItems);
        setDistricts(districtItems);
        setSelectedDistrict(null);
        setSelectedArea(null);
        setSelectedVillage("");
        setAreas([]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load room finder data");
      } finally {
        setLoading(false);
      }
    }

    loadRoomFinder();
  }, []);

  async function selectDistrict(district: District) {
    setSelectedDistrict(district);
    setSelectedArea(null);
    setSelectedVillage("");
    setSelectedListingId(null);
    setQuery("");
    setType("all");
    setSize("");
    setMinRent("");
    setMaxRent("");
    setDistance("");
    setGenderPreference("any");
    setMustHaveWater(false);
    setMustHaveElectricity(false);
    setMustBeFurnished(false);
    setAreas([]);
    setLoadingAreas(true);
    setError("");

    try {
      const areaItems = (await apiFetch(`/district-areas/district/${district.id}/active`)) as DistrictArea[];
      setAreas(areaItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load areas for this district");
    } finally {
      setLoadingAreas(false);
    }
  }

  function selectArea(area: DistrictArea) {
    setSelectedArea(area);
    setSelectedVillage("");
    setSelectedListingId(null);
    setQuery("");
  }

  function backToDistricts() {
    setSelectedDistrict(null);
    setSelectedArea(null);
    setSelectedVillage("");
    setSelectedListingId(null);
    setAreas([]);
    setQuery("");
  }

  function backToAreas() {
    setSelectedArea(null);
    setSelectedVillage("");
    setSelectedListingId(null);
    setQuery("");
  }

  const filteredListings = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const rentFloor = minRent ? Number(minRent) : null;
    const rentLimit = maxRent ? Number(maxRent) : null;
    const distanceTerm = distance.trim().toLowerCase();
    const areaTerm = selectedArea?.name.trim().toLowerCase() ?? "";
    const villageTerm = selectedVillage.trim().toLowerCase();

    return listings.filter((listing) => {
      const text = `${listing.title} ${listing.property_name ?? ""} ${listing.location_area} ${listing.room_size ?? ""} ${listing.description ?? ""}`.toLowerCase();
      const areaText = `${listing.location_area} ${listing.property_name ?? ""} ${listing.description ?? ""}`.toLowerCase();

      const matchesArea = areaTerm && areaText.includes(areaTerm);
      const matchesVillage = !villageTerm || areaText.includes(villageTerm);
      const matchesQuery = !normalized || text.includes(normalized);
      const matchesType = type === "all" || listing.room_type === type;
      const matchesSize = !size || (listing.room_size ?? "").toLowerCase().includes(size.toLowerCase());
      const matchesMinRent = !rentFloor || Number(listing.rent_price) >= rentFloor;
      const matchesRent = !rentLimit || Number(listing.rent_price) <= rentLimit;
      const matchesDistance = !distanceTerm || (listing.distance_from_nul ?? "").toLowerCase().includes(distanceTerm);
      const listingGender = (listing.gender_preference ?? "any").toLowerCase();
      const matchesGender = genderPreference === "any" || listingGender === "any" || listingGender === genderPreference;
      const matchesWater = !mustHaveWater || listing.water_available;
      const matchesElectricity = !mustHaveElectricity || listing.electricity_available;
      const matchesFurnished = !mustBeFurnished || listing.furnished;

      return (
        matchesArea &&
        matchesVillage &&
        matchesQuery &&
        matchesType &&
        matchesSize &&
        matchesMinRent &&
        matchesRent &&
        matchesDistance &&
        matchesGender &&
        matchesWater &&
        matchesElectricity &&
        matchesFurnished
      );
    });
  }, [distance, genderPreference, listings, maxRent, minRent, mustBeFurnished, mustHaveElectricity, mustHaveWater, query, selectedArea, selectedVillage, size, type]);

  const selectedListing = listings.find((listing) => listing.id === selectedListingId) ?? null;

  function updateApplication(key: keyof ApplicationForm, value: string) {
    setApplication((current) => ({ ...current, [key]: value }));
  }

  async function submitApplication(event: FormEvent) {
    event.preventDefault();

    if (!selectedListing) return;

    setSubmitting("application");
    setFormMessage("");
    setReservationLink("");
    try {
      const reservation = await apiFetch("/room-reservations/request", {
        method: "POST",
        body: JSON.stringify({
          listing_id: selectedListing.id,
          full_name: application.full_name,
          phone: application.phone,
          email: toNullable(application.email),
          preferred_response_method: application.preferred_response_method,
          message: toNullable(application.message)
        })
      }) as RoomReservation;
      setApplication(emptyApplication);
      setFormMessage(`Your request has been submitted. The landlord/caretaker will respond using your selected contact method. Reservation code: ${reservation.reservation_code}.`);
      setReservationLink(`#/reservation/${reservation.id}`);
    } catch (err) {
      setFormMessage(err instanceof Error ? err.message : "Application could not be submitted");
    } finally {
      setSubmitting("");
    }
  }

  return (
    <section className="page-stack">
      <div className="public-topbar">
        <div className="brand-mark light">
          <span>RL</span>
          <div>
            <strong>Rentalink</strong>
            <small>Room finder</small>
          </div>
        </div>

        <div className="public-actions">
          <a
            href={`#${returnTo}`}
            onClick={() => {
              if (returnTo === "/login" && user) logout();
            }}
          >
            {returnLabel}
          </a>
        </div>
      </div>

      <div className="page-header">
        <div>
          <p className="eyebrow">Public room finder</p>
          <h1>
            {selectedListing
              ? selectedListing.title
              : selectedArea
                ? `Find vacant rooms in ${selectedArea.name}${selectedVillage ? ` / ${selectedVillage}` : ""}`
                : selectedDistrict
                  ? `Choose an area in ${selectedDistrict.name}`
                  : "Select your district"}
          </h1>

          <p>
            {selectedListing
              ? "Send a private interest request for this exact room. The landlord or caretaker decides whether to send you the secure full application link."
              : selectedArea
                ? selectedArea.name === "Roma"
                  ? "Choose a Roma village, browse published vacant rooms, filter by price and room type, then request a room."
                  : "Browse published vacant rooms inside this area, filter by price and room type, then request a room."
                : selectedDistrict
                  ? "Choose an active area inside this district. Locked areas remain hidden until rollout."
                  : "Choose an active district first. Locked districts remain hidden until Rentalink officially rolls out there."}
          </p>
        </div>

        <div className="header-stat">
          <strong>
            {selectedListing
              ? money(selectedListing.rent_price)
              : selectedArea
                ? filteredListings.length
                : selectedDistrict
                  ? areas.length
                  : districts.length}
          </strong>
          <span>
            {selectedListing
              ? "monthly rent"
              : selectedArea
                ? "vacant rooms"
                : selectedDistrict
                  ? "active areas"
                  : "active districts"}
          </span>
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}

      {!loading && !error && !selectedListing && !selectedDistrict ? (
        <div className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">District rollout</p>
              <h2>Choose active district</h2>
            </div>
            <StatusPill value={`${districts.length}_active`} />
          </div>

          {districts.length > 0 ? (
            <>
              <div className="amenities compact">
                {districts.map((district) => (
                  <button className="chip-button" type="button" key={district.id} onClick={() => selectDistrict(district)}>
                    {district.name}
                  </button>
                ))}
              </div>

              <div className="data-state compact-state">
                Only districts activated by Admin are shown here. Select a district to view its active areas.
              </div>
            </>
          ) : (
            <div className="data-state">No active districts are available yet. Please check again later.</div>
          )}
        </div>
      ) : null}

      {!loading && !error && !selectedListing && selectedDistrict && !selectedArea ? (
        <div className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Selected district</p>
              <h2>{selectedDistrict.name}</h2>
            </div>

            <button className="secondary-button" type="button" onClick={backToDistricts}>
              Back to districts
            </button>
          </div>

          {loadingAreas ? <LoadingState /> : null}

          {!loadingAreas && areas.length > 0 ? (
            <>
              <div className="amenities compact">
                {areas.map((area) => (
                  <button className="chip-button" type="button" key={area.id} onClick={() => selectArea(area)}>
                    {area.name}
                  </button>
                ))}
              </div>

              <div className="data-state compact-state">
                Select an area inside {selectedDistrict.name} to view available rooms.
              </div>
            </>
          ) : null}

          {!loadingAreas && areas.length === 0 ? (
            <div className="data-state">
              No active areas are available in {selectedDistrict.name} yet.
            </div>
          ) : null}
        </div>
      ) : null}

      {!loading && !error && !selectedListing && selectedDistrict && selectedArea ? (
        <>
          <div className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Selected area</p>
                <h2>
                  {selectedDistrict.name} / {selectedArea.name}
                  {selectedVillage ? ` / ${selectedVillage}` : ""}
                </h2>
              </div>

              <button className="secondary-button" type="button" onClick={backToAreas}>
                Back to areas
              </button>
            </div>
          </div>

          {selectedArea.name === "Roma" ? (
            <div className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Roma villages</p>
                  <h2>Select village</h2>
                </div>
              </div>

              <div className="amenities compact">
                <button
                  className={`chip-button ${selectedVillage === "" ? "active" : ""}`}
                  type="button"
                  onClick={() => setSelectedVillage("")}
                >
                  All villages
                </button>

                {romaVillages.map((village) => (
                  <button
                    key={village}
                    className={`chip-button ${selectedVillage === village ? "active" : ""}`}
                    type="button"
                    onClick={() => setSelectedVillage(village)}
                  >
                    {village}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="finder-subnav">
            <div className="toolbar wide">
              <input placeholder="Search property, room, or description" value={query} onChange={(event) => setQuery(event.target.value)} />

              <select value={type} onChange={(event) => setType(event.target.value)}>
                <option value="all">All room types</option>
                <option value="single">Single</option>
                <option value="double">Double</option>
              </select>

              <input placeholder="Room size" value={size} onChange={(event) => setSize(event.target.value)} />
              <input placeholder="Min rent" inputMode="numeric" value={minRent} onChange={(event) => setMinRent(event.target.value)} />
              <input placeholder="Max rent" inputMode="numeric" value={maxRent} onChange={(event) => setMaxRent(event.target.value)} />
              <input placeholder="Distance from NUL" value={distance} onChange={(event) => setDistance(event.target.value)} />
              <select value={genderPreference} onChange={(event) => setGenderPreference(event.target.value as "any" | "male" | "female")}>
                <option value="any">Any gender</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>

              <label className="inline-check">
                <input type="checkbox" checked={mustHaveWater} onChange={(event) => setMustHaveWater(event.target.checked)} /> Water
              </label>

              <label className="inline-check">
                <input type="checkbox" checked={mustHaveElectricity} onChange={(event) => setMustHaveElectricity(event.target.checked)} /> Electricity
              </label>

              <label className="inline-check">
                <input type="checkbox" checked={mustBeFurnished} onChange={(event) => setMustBeFurnished(event.target.checked)} /> Furnished
              </label>
            </div>
          </div>

          {filteredListings.length > 0 ? (
            <div className="listing-grid">
              {filteredListings.map((listing) => (
                <article className="listing-card" key={listing.id}>
                  <div>
                    <div className="card-topline">
                      <StatusPill value="available" />
                      <StatusPill value="available_now" />
                      <StatusPill value="public" />
                      <span>{listing.distance_from_nul ?? "Near NUL"}</span>
                    </div>

                    <h2>{roomLabel(listing)} - {listing.room_size} {listing.room_type}</h2>
                    <p>{listing.property_name ?? "Line-house"} - {listing.location_area}</p>
                  </div>

                  <div className="room-photo-strip">
                    <div className="room-photo-frame">
                      <span>{roomLabel(listing)}</span>
                      <strong>{money(listing.rent_price)}</strong>
                    </div>
                  </div>

                  <dl className="detail-grid">
                    <div><dt>Rent</dt><dd>{money(listing.rent_price)}</dd></div>
                    <div><dt>Deposit</dt><dd>{money(listing.deposit_amount)}</dd></div>
                    <div><dt>Tenant</dt><dd>{listing.allowed_tenant_type.replace("_", " ")}</dd></div>
                    <div><dt>Gender</dt><dd>{(listing.gender_preference ?? "any").replace("_", " ")}</dd></div>
                    <div><dt>Area</dt><dd>{listing.location_area}</dd></div>
                  </dl>

                  <div className="amenities compact">
                    {listing.water_available ? <span>Water</span> : null}
                    {listing.electricity_available ? <span>Electricity</span> : null}
                    {listing.internet_included ? <span>Internet</span> : null}
                    {listing.furnished ? <span>Furnished</span> : null}
                    {listing.parking_available ? <span>Parking</span> : null}
                  </div>

                  <footer>
                    <strong>{listing.contact_phone ?? "Contact after request"}</strong>
                    {listing.contact_phone ? <a className="text-button" href={`tel:${listing.contact_phone}`}>Call</a> : null}
                    {listing.contact_phone ? <a className="text-button" href={`https://wa.me/${listing.contact_phone.replace(/\D/g, "")}`} target="_blank" rel="noreferrer">WhatsApp</a> : null}

                    <button className="secondary-button" type="button" onClick={() => setSelectedListingId(listing.id)}>
                      Request Room
                    </button>
                  </footer>
                </article>
              ))}
            </div>
          ) : (
            <div className="data-state">No vacant rooms match this area or filters.</div>
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
              <StatusPill value="available" />
              <StatusPill value="available_now" />
              <StatusPill value="public" />
              <span>{selectedListing.property_name ?? "Line-house"} - {selectedListing.location_area}</span>
            </div>

            <h2>{roomLabel(selectedListing)} - {selectedListing.room_size} {selectedListing.room_type}</h2>
            <p>{selectedListing.description}</p>

            <dl className="detail-grid">
              <div><dt>Monthly rent</dt><dd>{money(selectedListing.rent_price)}</dd></div>
              <div><dt>Deposit</dt><dd>{money(selectedListing.deposit_amount)}</dd></div>
              <div><dt>Distance</dt><dd>{selectedListing.distance_from_nul ?? "Ask landlord"}</dd></div>
              <div><dt>Contact</dt><dd>{selectedListing.contact_phone ?? "Provided after review"}</dd></div>
            </dl>

            <div className="amenities">
              {selectedListing.water_available ? <span>Water available</span> : null}
              {selectedListing.electricity_available ? <span>Electricity available</span> : null}
              {selectedListing.internet_included ? <span>Internet included</span> : null}
              {selectedListing.furnished ? <span>Furnished</span> : null}
              {selectedListing.parking_available ? <span>Parking available</span> : null}
              {selectedListing.pets_allowed ? <span>Pets allowed</span> : null}
              {selectedListing.security_features ? <span>{selectedListing.security_features}</span> : null}
              {selectedListing.house_rules ? <span>{selectedListing.house_rules}</span> : null}
            </div>
          </article>

          <form className="panel form-panel request-panel" onSubmit={submitApplication}>
            <div>
              <p className="eyebrow">Private room request</p>
              <h2>Request this room</h2>
              <p>Send basic details first. The landlord or caretaker reviews your request before any deposit payment is allowed.</p>
              <p className="privacy-note">Your information is private and only visible to the landlord/caretaker of this listing.</p>
            </div>

            <label>Full name<input required value={application.full_name} onChange={(event) => updateApplication("full_name", event.target.value)} /></label>
            <label>Phone<input required value={application.phone} onChange={(event) => updateApplication("phone", event.target.value)} /></label>
            <label>Email {application.preferred_response_method === "email" ? "" : "optional"}<input required={application.preferred_response_method === "email"} type="email" value={application.email} onChange={(event) => updateApplication("email", event.target.value)} /></label>

            <label>Preferred response method<select required value={application.preferred_response_method} onChange={(event) => updateApplication("preferred_response_method", event.target.value as ApplicationForm["preferred_response_method"])}>
              <option value="phone_call">Phone call</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="email">Email</option>
              <option value="sms">SMS</option>
            </select></label>

            <div className="data-state compact-state">{responseHelp[application.preferred_response_method]}</div>
            <label>Message<textarea value={application.message} onChange={(event) => updateApplication("message", event.target.value)} /></label>

            <button className="primary-button" disabled={submitting === "application"} type="submit">
              {submitting === "application" ? "Submitting..." : "Request Room"}
            </button>
            {formMessage ? <div className="data-state">{formMessage}{reservationLink ? <><br /><a href={reservationLink}>View request status</a></> : null}</div> : null}
          </form>
        </div>
      ) : null}
    </section>
  );
}
