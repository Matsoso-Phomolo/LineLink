import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import type { DashboardSummary, NotificationItem, PropertyItem, Room } from "../../types";

export function LandlordDashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [properties, setProperties] = useState<PropertyItem[]>([]);
  const [selectedRooms, setSelectedRooms] = useState<string[]>([]);
  const [pushNote, setPushNote] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([apiFetch("/dashboard/summary"), apiFetch("/notifications"), apiFetch("/rooms"), apiFetch("/properties")])
      .then(([dashboard, notes, roomItems, propertyItems]) => {
        setSummary(dashboard);
        setNotifications(notes);
        setRooms(roomItems);
        setProperties(propertyItems);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load dashboard"))
      .finally(() => setLoading(false));
  }, []);
  const vacantRooms = rooms.filter((room) => room.status === "vacant");
  const propertyById = Object.fromEntries(properties.map((property) => [property.id, property]));

  async function pushVacantRooms(all: boolean) {
    const roomsToPush = all ? vacantRooms : vacantRooms.filter((room) => selectedRooms.includes(room.id));
    if (roomsToPush.length === 0) {
      setNotice("Choose at least one vacant room.");
      return;
    }
    try {
      await Promise.all(roomsToPush.map((room) => {
        const property = propertyById[room.property_id];
        return apiFetch("/listings", {
          method: "POST",
          body: JSON.stringify({
            property_id: room.property_id,
            room_id: room.id,
            title: `${room.room_number} ${room.room_size ?? ""} ${room.room_type} room in ${property?.location_area ?? "Roma"}`.replace(/\s+/g, " ").trim(),
            description: pushNote || `Vacant ${room.room_type} room available at ${property?.name ?? "LineLink property"}.`,
            rent_price: room.rent_price,
            deposit_amount: room.deposit_amount,
            room_type: room.room_type,
            room_size: room.room_size,
            location_area: property?.location_area ?? "Roma",
            allowed_tenant_type: "both",
            distance_from_nul: property?.distance_from_nul ?? null,
            contact_phone: null,
            water_available: true,
            electricity_available: true,
            status: "published",
            is_public: true
          })
        });
      }));
      setNotice("Vacant rooms pushed to public verification queue.");
      setSelectedRooms([]);
      setPushNote("");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not push vacant rooms");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Landlord dashboard</p>
          <h1>Portfolio snapshot</h1>
          <p>Room availability, payments, listings, and tenant operations in one place.</p>
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}
      {summary ? (
        <>
          <div className="metric-grid">
            <Metric label="Properties" value={summary.properties} />
            <Metric label="Rooms" value={summary.rooms} />
            <Metric label="Vacant" value={summary.vacant_rooms} />
            <Metric label="Occupied" value={summary.occupied_rooms} />
            <Metric label="Unpaid dues" value={summary.unpaid_rent_dues} />
            <Metric label="Pending payments" value={summary.pending_payment_submissions} />
            <Metric label="Public listings" value={summary.published_listings} />
            <Metric label="Applications" value={summary.pending_applications} />
            <Metric label="Room requests" value={summary.pending_room_requests} />
            <Metric label="Overdue rent" value={summary.overdue_rent_dues} />
            <Metric label="Maintenance" value={summary.maintenance_tickets} />
            <Metric label="Tenants" value={summary.total_tenants} />
          </div>
          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Public marketplace</p>
                <h2>Push vacant rooms to public</h2>
              </div>
              <button type="button" onClick={() => pushVacantRooms(true)}>Push all vacant</button>
            </div>
            <p>Only vacant rooms are selectable. New listings enter pending verification before public visibility.</p>
            <label>Clarification note<textarea value={pushNote} onChange={(event) => setPushNote(event.target.value)} placeholder="Add details for admin verification or room seekers" /></label>
            <div className="amenities compact">
              <label className="inline-check">Room photos<input type="file" multiple accept="image/*" /></label>
              <label className="inline-check">Line/property photos<input type="file" multiple accept="image/*" /></label>
            </div>
            <div className="list-stack compact-list">
              {vacantRooms.map((room) => (
                <label className="inline-check" key={room.id}>
                  <input type="checkbox" checked={selectedRooms.includes(room.id)} onChange={(event) => setSelectedRooms((current) => event.target.checked ? [...current, room.id] : current.filter((id) => id !== room.id))} />
                  {room.room_number} - {room.room_type} - M{Number(room.rent_price).toLocaleString()} - {propertyById[room.property_id]?.location_area ?? "Unknown"}
                </label>
              ))}
            </div>
            <button className="primary-button" type="button" onClick={() => pushVacantRooms(false)}>Push selected vacant rooms</button>
          </section>
          <section className="panel">
            <h2>Recent notifications</h2>
            <div className="list-stack">
              {notifications.slice(0, 5).map((note) => (
                <article key={note.id} className="row-item">
                  <div>
                    <strong>{note.title}</strong>
                    <p>{note.body}</p>
                  </div>
                  <span>{note.category}</span>
                </article>
              ))}
            </div>
          </section>
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
