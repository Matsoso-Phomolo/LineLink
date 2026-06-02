import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import type { PropertyItem, Room } from "../../types";

function naturalRoomCompare(left: Room, right: Room) {
  const typeRank = (room: Room) => (room.room_type === "single" ? 0 : room.room_type === "double" ? 1 : 2);
  const leftType = typeRank(left);
  const rightType = typeRank(right);
  if (left.property_id !== right.property_id) return left.property_id.localeCompare(right.property_id);
  if (leftType !== rightType) return leftType - rightType;
  return left.room_number.localeCompare(right.room_number, undefined, {
    numeric: true,
    sensitivity: "base"
  });
}

export function RoomsPage() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [properties, setProperties] = useState<PropertyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
    () => rooms.slice().sort(naturalRoomCompare),
    [rooms]
  );
  const propertyById = useMemo(() => Object.fromEntries(properties.map((property) => [property.id, property])), [properties]);

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Rentalink approved inventory</p>
          <h1>Room inventory</h1>
          <p>View approved room infrastructure exactly as verified by District Administration.</p>
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}

      <div className="table-panel">
        <table>
          <thead>
            <tr>
              <th>Property</th>
              <th>Room</th>
              <th>Type</th>
            </tr>
          </thead>
          <tbody>
            {visibleRooms.length === 0 ? (
              <tr>
                <td colSpan={3}>No approved rooms are available.</td>
              </tr>
            ) : null}
            {visibleRooms.map((room) => {
              const property = propertyById[room.property_id];
              return (
                <tr key={room.id}>
                  <td>
                    <strong>{property?.name ?? "Unknown property"}</strong>
                    <br />
                    <small>{property?.location_area ?? "Unknown location"}</small>
                  </td>
                  <td>{room.room_number}</td>
                  <td>{room.room_type}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
