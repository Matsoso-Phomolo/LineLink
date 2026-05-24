import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { PropertyItem, Room } from "../../types";

type RoomForm = {
  id?: string;
  property_id: string;
  room_number: string;
  status: Room["status"];
  room_type: Room["room_type"];
  room_size: string;
  rent_price: string;
  deposit_amount: string;
  notes: string;
};

type BulkRoomForm = {
  property_id: string;
  prefix: string;
  start_number: string;
  room_size: string;
  single_count: string;
  single_rent: string;
  single_deposit: string;
  double_count: string;
  double_rent: string;
  double_deposit: string;
};

const emptyRoom: RoomForm = {
  property_id: "",
  room_number: "",
  status: "vacant",
  room_type: "single",
  room_size: "medium",
  rent_price: "",
  deposit_amount: "",
  notes: ""
};

const emptyBulk: BulkRoomForm = {
  property_id: "",
  prefix: "A",
  start_number: "101",
  room_size: "medium",
  single_count: "0",
  single_rent: "",
  single_deposit: "",
  double_count: "0",
  double_rent: "",
  double_deposit: ""
};

function formFromRoom(room: Room): RoomForm {
  return {
    id: room.id,
    property_id: room.property_id,
    room_number: room.room_number,
    status: room.status,
    room_type: room.room_type,
    room_size: room.room_size ?? "",
    rent_price: String(room.rent_price),
    deposit_amount: String(room.deposit_amount),
    notes: room.notes ?? ""
  };
}

export function RoomsPage() {
  const { user } = useAuth();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [properties, setProperties] = useState<PropertyItem[]>([]);
  const [form, setForm] = useState<RoomForm>(emptyRoom);
  const [bulk, setBulk] = useState<BulkRoomForm>(emptyBulk);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [status, setStatus] = useState("all");
  const [busyId, setBusyId] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [roomItems, propertyItems] = await Promise.all([
        apiFetch("/rooms") as Promise<Room[]>,
        apiFetch("/properties") as Promise<PropertyItem[]>
      ]);
      setRooms(roomItems);
      setProperties(propertyItems);
      setForm((current) => current.property_id || propertyItems.length === 0 ? current : { ...current, property_id: propertyItems[0].id });
      setBulk((current) => current.property_id || propertyItems.length === 0 ? current : { ...current, property_id: propertyItems[0].id });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load rooms");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const visibleRooms = useMemo(() => rooms.filter((room) => status === "all" || room.status === status), [rooms, status]);
  const propertyById = useMemo(() => Object.fromEntries(properties.map((property) => [property.id, property])), [properties]);
  const canManageInventory = user?.role === "landlord" || user?.role === "admin";

  function update<K extends keyof RoomForm>(key: K, value: RoomForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function updateBulk<K extends keyof BulkRoomForm>(key: K, value: BulkRoomForm[K]) {
    setBulk((current) => ({ ...current, [key]: value }));
  }

  async function saveRoom(event: FormEvent) {
    event.preventDefault();
    setNotice("");
    const payload = {
      property_id: form.property_id,
      room_number: form.room_number,
      status: form.status,
      room_type: form.room_type,
      room_size: form.room_size || null,
      rent_price: Number(form.rent_price),
      deposit_amount: Number(form.deposit_amount || 0),
      notes: form.notes || null
    };
    try {
      if (form.id) {
        await apiFetch(`/rooms/${form.id}`, { method: "PUT", body: JSON.stringify(payload) });
        setNotice("Room updated.");
      } else {
        await apiFetch("/rooms", { method: "POST", body: JSON.stringify(payload) });
        setNotice("Room added.");
      }
      setForm({ ...emptyRoom, property_id: properties[0]?.id ?? "" });
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not save room");
    }
  }

  async function createBulkRooms(event: FormEvent) {
    event.preventDefault();
    setNotice("");
    const singleCount = Number(bulk.single_count || 0);
    const doubleCount = Number(bulk.double_count || 0);
    const startNumber = Number(bulk.start_number || 1);
    const total = singleCount + doubleCount;
    if (total <= 0) {
      setNotice("Enter at least one single or double room.");
      return;
    }
    const tasks: Array<{ room_type: Room["room_type"]; rent_price: string; deposit_amount: string }> = [
      ...Array.from({ length: singleCount }, () => ({ room_type: "single" as const, rent_price: bulk.single_rent, deposit_amount: bulk.single_deposit })),
      ...Array.from({ length: doubleCount }, () => ({ room_type: "double" as const, rent_price: bulk.double_rent, deposit_amount: bulk.double_deposit }))
    ];
    try {
      await Promise.all(tasks.map((item, index) => apiFetch("/rooms", {
        method: "POST",
        body: JSON.stringify({
          property_id: bulk.property_id,
          room_number: `${bulk.prefix}-${startNumber + index}`,
          status: "vacant",
          room_type: item.room_type,
          room_size: bulk.room_size,
          rent_price: Number(item.rent_price),
          deposit_amount: Number(item.deposit_amount || item.rent_price || 0),
          notes: `Bulk-created ${item.room_type} room`
        })
      })));
      setNotice(`${total} rooms created for this line.`);
      setBulk({ ...emptyBulk, property_id: properties[0]?.id ?? "" });
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not create bulk rooms");
    }
  }

  async function quickStatus(room: Room, nextStatus: Room["status"]) {
    setBusyId(room.id);
    setNotice("");
    try {
      await apiFetch(`/rooms/${room.id}`, { method: "PUT", body: JSON.stringify({ status: nextStatus }) });
      setNotice(nextStatus === "occupied" ? "Room marked occupied. Any active public listing was hidden automatically." : `Room marked ${nextStatus}.`);
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update room");
    } finally {
      setBusyId("");
    }
  }

  async function removeRoom(room: Room) {
    setBusyId(room.id);
    setNotice("");
    try {
      await apiFetch(`/rooms/${room.id}`, { method: "DELETE" });
      setNotice("Room removed.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not remove room");
    } finally {
      setBusyId("");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Rooms</p>
          <h1>Room inventory</h1>
          <p>Add rooms under the correct line location, edit rent/deposit, and control whether rooms are vacant, occupied, or under maintenance.</p>
        </div>
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="all">All statuses</option>
          <option value="vacant">Vacant</option>
          <option value="occupied">Occupied</option>
          <option value="maintenance">Maintenance</option>
        </select>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}

      {canManageInventory ? <form className="panel form-panel" onSubmit={createBulkRooms}>
        <div>
          <p className="eyebrow">Line setup</p>
          <h2>Add many rooms at once</h2>
          <p>Enter how many single and double rooms this line has, then LineLink creates the room inventory with prices and deposits.</p>
        </div>
        <div className="form-grid">
          <label>Property/location<select required value={bulk.property_id} onChange={(event) => updateBulk("property_id", event.target.value)}>
            <option value="">Choose property</option>
            {properties.map((property) => <option key={property.id} value={property.id}>{property.name} - {property.location_area}</option>)}
          </select></label>
          <label>Room size<select value={bulk.room_size} onChange={(event) => updateBulk("room_size", event.target.value)}>
            <option value="small">Small</option>
            <option value="medium">Medium</option>
            <option value="large">Large</option>
          </select></label>
        </div>
        <div className="form-grid">
          <label>Room prefix<input value={bulk.prefix} onChange={(event) => updateBulk("prefix", event.target.value)} placeholder="A" /></label>
          <label>Starting number<input inputMode="numeric" value={bulk.start_number} onChange={(event) => updateBulk("start_number", event.target.value)} placeholder="101" /></label>
        </div>
        <div className="form-grid">
          <label>Number of single rooms<input inputMode="numeric" value={bulk.single_count} onChange={(event) => updateBulk("single_count", event.target.value)} /></label>
          <label>Single room price<input inputMode="numeric" value={bulk.single_rent} onChange={(event) => updateBulk("single_rent", event.target.value)} /></label>
        </div>
        <label>Single room deposit<input inputMode="numeric" value={bulk.single_deposit} onChange={(event) => updateBulk("single_deposit", event.target.value)} placeholder="Defaults to single room price" /></label>
        <div className="form-grid">
          <label>Number of double rooms<input inputMode="numeric" value={bulk.double_count} onChange={(event) => updateBulk("double_count", event.target.value)} /></label>
          <label>Double room price<input inputMode="numeric" value={bulk.double_rent} onChange={(event) => updateBulk("double_rent", event.target.value)} /></label>
        </div>
        <label>Double room deposit<input inputMode="numeric" value={bulk.double_deposit} onChange={(event) => updateBulk("double_deposit", event.target.value)} placeholder="Defaults to double room price" /></label>
        <button className="primary-button" disabled={properties.length === 0} type="submit">Create room inventory</button>
      </form> : null}

      {form.id ? <form className="panel form-panel" onSubmit={saveRoom}>
        <div>
          <p className="eyebrow">Edit room</p>
          <h2>{form.room_number}</h2>
        </div>
        <div className="form-grid">
          <label>Property/location<select required value={form.property_id} onChange={(event) => update("property_id", event.target.value)}>
            <option value="">Choose property</option>
            {properties.map((property) => <option key={property.id} value={property.id}>{property.name} - {property.location_area}</option>)}
          </select></label>
          <label>Room number<input required value={form.room_number} onChange={(event) => update("room_number", event.target.value)} placeholder="A-101" /></label>
        </div>
        <div className="form-grid">
          <label>Status<select value={form.status} onChange={(event) => update("status", event.target.value as Room["status"])}>
            <option value="vacant">Vacant</option>
            <option value="occupied">Occupied</option>
            <option value="maintenance">Maintenance</option>
          </select></label>
          <label>Room type<select value={form.room_type} onChange={(event) => update("room_type", event.target.value as Room["room_type"])}>
            <option value="single">Single</option>
            <option value="double">Double</option>
          </select></label>
        </div>
        <div className="form-grid">
          <label>Room size<select value={form.room_size} onChange={(event) => update("room_size", event.target.value)}>
            <option value="small">Small</option>
            <option value="medium">Medium</option>
            <option value="large">Large</option>
          </select></label>
          <label>Monthly rent<input required inputMode="numeric" value={form.rent_price} onChange={(event) => update("rent_price", event.target.value)} /></label>
        </div>
        <label>Deposit<input inputMode="numeric" value={form.deposit_amount} onChange={(event) => update("deposit_amount", event.target.value)} /></label>
        <label>Notes<textarea value={form.notes} onChange={(event) => update("notes", event.target.value)} /></label>
        <div className="review-actions">
          <button className="primary-button" disabled={properties.length === 0} type="submit">{form.id ? "Save room" : "Add room"}</button>
          {form.id ? <button type="button" onClick={() => setForm({ ...emptyRoom, property_id: properties[0]?.id ?? "" })}>Cancel edit</button> : null}
        </div>
      </form> : null}

      <div className="table-panel">
        <table>
          <thead>
            <tr>
              <th>Room</th>
              <th>Location</th>
              <th>Status</th>
              <th>Type</th>
              <th>Size</th>
              <th>Rent</th>
              <th>Deposit</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleRooms.map((room) => (
              <tr key={room.id}>
                <td>{room.room_number}</td>
                <td>{propertyById[room.property_id]?.location_area ?? "Unknown"}</td>
                <td><StatusPill value={room.status} /></td>
                <td>{room.room_type}</td>
                <td>{room.room_size}</td>
                <td>M{Number(room.rent_price).toLocaleString()}</td>
                <td>M{Number(room.deposit_amount).toLocaleString()}</td>
                <td>
                  <div className="table-actions">
                    {canManageInventory ? <button type="button" onClick={() => setForm(formFromRoom(room))}>Edit</button> : null}
                    <button type="button" disabled={busyId === room.id} onClick={() => quickStatus(room, "vacant")}>Vacant</button>
                    <button type="button" disabled={busyId === room.id} onClick={() => quickStatus(room, "maintenance")}>Maintenance</button>
                    <button type="button" disabled={busyId === room.id} onClick={() => quickStatus(room, "occupied")}>Occupied</button>
                    {canManageInventory ? <button type="button" disabled={busyId === room.id || room.status === "occupied"} onClick={() => removeRoom(room)}>Remove</button> : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
