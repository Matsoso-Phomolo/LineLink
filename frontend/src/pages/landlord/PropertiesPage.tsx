import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { PropertyItem, Room } from "../../types";

export function PropertiesPage() {
  const [properties, setProperties] = useState<PropertyItem[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [propertyItems, roomItems] = await Promise.all([
        apiFetch("/properties") as Promise<PropertyItem[]>,
        apiFetch("/rooms") as Promise<Room[]>
      ]);
      setProperties(propertyItems);
      setRooms(roomItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load approved properties");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const roomsByProperty = useMemo(() => {
    const grouped: Record<string, Room[]> = {};
    rooms.forEach((room) => {
      grouped[room.property_id] = [...(grouped[room.property_id] ?? []), room];
    });
    return grouped;
  }, [rooms]);

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Rentalink verified locations</p>
          <h1>Properties and apartments</h1>
          <p>View approved properties created from landlord verification records. Property infrastructure is controlled by National and District administrators.</p>
        </div>
        <div className="header-stat">
          <strong>{properties.length}</strong>
          <span>approved locations</span>
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}

      <div className="data-state">
        Landlords can review verified location details, room totals, and operational readiness. Add, edit, and delete actions are intentionally unavailable to protect verified property data.
      </div>

      <div className="list-stack">
        {properties.length === 0 && !loading ? <div className="data-state">No verified properties are available yet. Administrators create properties after landlord verification.</div> : null}
        {properties.map((property) => {
          const propertyRooms = roomsByProperty[property.id] ?? [];
          const vacant = propertyRooms.filter((room) => room.status === "vacant").length;
          const maintenance = propertyRooms.filter((room) => room.status === "maintenance").length;
          const occupied = propertyRooms.length - vacant - maintenance;
          return (
            <article className="row-item rich" key={property.id}>
              <div>
                <div className="card-topline">
                  <StatusPill value="verified" />
                  <span>{property.location_area}</span>
                </div>
                <strong>{property.name}</strong>
                <p>{property.address ?? "Address not set"}</p>
                <small>{property.distance_from_nul ?? "Distance from NUL not set"}</small>
              </div>
              <div className="review-actions">
                <span>{propertyRooms.length} rooms</span>
                <span>{vacant} vacant</span>
                <span>{occupied} occupied</span>
                <span>{maintenance} maintenance</span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
