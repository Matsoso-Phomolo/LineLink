import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { Listing, PropertyItem, Room, Tenant } from "../../types";

type Occupancy = {
  id: string;
  tenant_id: string;
  room_id: string;
  status: "active" | "ended" | "transferred";
  move_in_date: string;
  move_out_date?: string | null;
};

const occupiedStatuses = new Set(["occupied", "partially_occupied", "full"]);

function naturalRoomCompare(left: Room, right: Room) {
  return left.room_number.localeCompare(right.room_number, undefined, {
    numeric: true,
    sensitivity: "base"
  });
}

export function RoomsPage() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [properties, setProperties] = useState<PropertyItem[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [occupancies, setOccupancies] = useState<Occupancy[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [status, setStatus] = useState("all");
  const [busyId, setBusyId] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [roomItems, propertyItems, listingItems, occupancyItems, tenantItems] = await Promise.all([
        apiFetch("/rooms") as Promise<Room[]>,
        apiFetch("/properties") as Promise<PropertyItem[]>,
        apiFetch("/listings/mine") as Promise<Listing[]>,
        apiFetch("/occupancies") as Promise<Occupancy[]>,
        apiFetch("/tenants") as Promise<Tenant[]>
      ]);
      setRooms(roomItems);
      setProperties(propertyItems);
      setListings(listingItems);
      setOccupancies(occupancyItems);
      setTenants(tenantItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load approved room inventory");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const visibleRooms = useMemo(
    () => rooms.filter((room) => status === "all" || room.status === status).slice().sort(naturalRoomCompare),
    [rooms, status]
  );
  const propertyById = useMemo(() => Object.fromEntries(properties.map((property) => [property.id, property])), [properties]);
  const tenantById = useMemo(() => Object.fromEntries(tenants.map((tenant) => [tenant.id, tenant])), [tenants]);
  const activeOccupancyByRoom = useMemo(() => {
    const entries = occupancies
      .filter((occupancy) => occupancy.status === "active")
      .map((occupancy) => [occupancy.room_id, occupancy] as const);
    return Object.fromEntries(entries);
  }, [occupancies]);
  const listingByRoom = useMemo(() => {
    const activeListings = listings
      .filter((listing) => listing.status !== "archived")
      .map((listing) => [listing.room_id, listing] as const);
    return Object.fromEntries(activeListings);
  }, [listings]);

  async function publishVacantRoom(room: Room) {
    const property = propertyById[room.property_id];
    if (!property) {
      setNotice("Property information is missing for this room.");
      return;
    }
    setBusyId(room.id);
    setNotice("");
    try {
      await apiFetch("/listings", {
        method: "POST",
        body: JSON.stringify({
          property_id: room.property_id,
          room_id: room.id,
          title: `${room.room_number} ${room.room_type} room in ${property.location_area}`.replace(/\s+/g, " ").trim(),
          description: `Approved vacant room at ${property.name}.`,
          rent_price: room.rent_price,
          deposit_amount: room.deposit_amount,
          room_type: room.room_type,
          room_size: room.room_size,
          location_area: property.location_area,
          allowed_tenant_type: "both",
          distance_from_nul: property.distance_from_nul ?? null,
          contact_phone: null,
          water_available: true,
          electricity_available: true,
          status: "published",
          is_public: true
        })
      });
      setNotice("Vacant room published to the public Room Finder.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not publish this vacant room");
    } finally {
      setBusyId("");
    }
  }

  async function updateRoomStatus(room: Room, nextStatus: "vacant" | "occupied" | "maintenance") {
    setBusyId(room.id);
    setNotice("");
    try {
      await apiFetch(`/rooms/${room.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus })
      });
      setNotice(`${room.room_number} marked ${nextStatus}.`);
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update room status");
    } finally {
      setBusyId("");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Rentalink approved inventory</p>
          <h1>Room inventory</h1>
          <p>View approved rooms created from verified property information. Property and room infrastructure is controlled by administrators.</p>
        </div>
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="all">All statuses</option>
          <option value="vacant">Vacant</option>
          <option value="occupied">Occupied</option>
          <option value="partially_occupied">Partially occupied</option>
          <option value="full">Full</option>
          <option value="maintenance">Maintenance</option>
          <option value="reserved">Reserved</option>
        </select>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}

      <div className="data-state">
        Landlords can view room details, tenant assignment, occupancy state, listing status, maintenance state, and rent figures. Creating, editing, or deleting property infrastructure is handled by National and District administrators from verified landlord records.
      </div>

      <div className="table-panel">
        <table>
          <thead>
            <tr>
              <th>Property</th>
              <th>Room</th>
              <th>Type</th>
              <th>Rent</th>
              <th>Deposit</th>
              <th>Occupancy</th>
              <th>Tenant</th>
              <th>Listing</th>
              <th>Maintenance</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleRooms.length === 0 ? (
              <tr>
                <td colSpan={10}>No approved rooms match this filter.</td>
              </tr>
            ) : null}
            {visibleRooms.map((room) => {
              const property = propertyById[room.property_id];
              const occupancy = activeOccupancyByRoom[room.id];
              const tenant = occupancy ? tenantById[occupancy.tenant_id] : null;
              const listing = listingByRoom[room.id];
              const canPublish = room.status === "vacant" && !listing;
              const hasActiveTenant = Boolean(occupancy);
              return (
                <tr key={room.id}>
                  <td>
                    <strong>{property?.name ?? "Unknown property"}</strong>
                    <br />
                    <small>{property?.location_area ?? "Unknown location"}</small>
                  </td>
                  <td>{room.room_number}</td>
                  <td>{room.room_type}{room.room_size ? ` / ${room.room_size}` : ""}</td>
                  <td>M{Number(room.rent_price).toLocaleString()}</td>
                  <td>M{Number(room.deposit_amount).toLocaleString()}</td>
                  <td><StatusPill value={room.status} /></td>
                  <td>
                    {tenant ? (
                      <>
                        <strong>{tenant.full_name}</strong>
                        <br />
                        <small>{tenant.phone}</small>
                      </>
                    ) : occupiedStatuses.has(room.status) ? "Assigned tenant not loaded" : "No active tenant"}
                  </td>
                  <td>{listing ? <StatusPill value={listing.status} /> : "Not listed"}</td>
                  <td>{room.status === "maintenance" ? <StatusPill value="maintenance" /> : "No active maintenance flag"}</td>
                  <td>
                    <div className="table-actions">
                      <button type="button" disabled={busyId === room.id} onClick={() => setNotice(`Viewing ${room.room_number} under ${property?.name ?? "approved property"}.`)}>
                        View details
                      </button>
                      <button type="button" disabled={!tenant} onClick={() => setNotice(tenant ? `${tenant.full_name} is assigned to ${room.room_number}.` : "No active tenant assigned.")}>
                        View tenant
                      </button>
                      <button type="button" disabled={!canPublish || busyId === room.id} onClick={() => publishVacantRoom(room)}>
                        Publish listing
                      </button>
                      <button type="button" disabled={room.status === "vacant" || hasActiveTenant || busyId === room.id} title={hasActiveTenant ? "End the active tenant or lease before marking vacant." : undefined} onClick={() => updateRoomStatus(room, "vacant")}>
                        Mark Vacant
                      </button>
                      <button type="button" disabled={room.status === "occupied" || busyId === room.id} onClick={() => updateRoomStatus(room, "occupied")}>
                        Mark Occupied
                      </button>
                      <button type="button" disabled={room.status === "maintenance" || busyId === room.id} onClick={() => updateRoomStatus(room, "maintenance")}>
                        Mark Maintenance
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
