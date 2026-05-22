import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client";
import { StatusPill } from "./StatusPill";
import type { Listing } from "../types";

function money(value: number) {
  return `M${Number(value).toLocaleString()}`;
}

function listingRoomLabel(listing: Listing) {
  return listing.room_number ?? listing.title.match(/[A-Z]-\d{3}/i)?.[0] ?? listing.title;
}

export function VacantRoomsPreview() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/public/listings")
      .then((items: Listing[]) => setListings(items.slice(0, 4)))
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load vacant rooms"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="vacant-preview" aria-labelledby="vacant-preview-title">
      <div className="vacant-preview-header">
        <div>
          <p className="eyebrow">Room finder</p>
          <h3 id="vacant-preview-title">Vacant Rooms</h3>
        </div>
        <Link to="/rooms">View all rooms</Link>
      </div>

      {loading ? (
        <div className="vacant-preview-list" aria-label="Loading vacant rooms">
          {[0, 1, 2].map((item) => (
            <div className="vacant-room-skeleton" key={item} />
          ))}
        </div>
      ) : error ? (
        <p className="vacant-empty">Vacant rooms could not be loaded right now.</p>
      ) : listings.length === 0 ? (
        <p className="vacant-empty">No public vacant rooms are available yet.</p>
      ) : (
        <div className="vacant-preview-list">
          {listings.map((listing) => (
            <article className="vacant-room-mini" key={listing.id}>
              <div>
                <strong>{listingRoomLabel(listing)}</strong>
                <span>{listing.property_name ?? listing.location_area} · {listing.location_area}</span>
              </div>
              <div>
                <b>{money(listing.rent_price)}</b>
                <StatusPill value="vacant" />
              </div>
            </article>
          ))}
        </div>
      )}

      <Link className="primary-button link-button" to="/rooms">
        Find vacant rooms
      </Link>
    </section>
  );
}
