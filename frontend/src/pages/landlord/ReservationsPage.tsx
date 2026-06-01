import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { RoomReservation } from "../../types";

export function ReservationsPage() {
  const [reservations, setReservations] = useState<RoomReservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [decisionForms, setDecisionForms] = useState<Record<string, { amount: string; note: string }>>({});

  async function load() {
    setLoading(true);
    try {
      const items = await apiFetch("/landlord/reservations") as RoomReservation[];
      setReservations(items);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load reservations");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function formFor(reservation: RoomReservation) {
    return decisionForms[reservation.id] ?? { amount: reservation.reservation_amount ? String(reservation.reservation_amount) : "", note: "" };
  }

  function updateDecision(reservation: RoomReservation, key: "amount" | "note", value: string) {
    setDecisionForms((current) => ({ ...current, [reservation.id]: { ...formFor(reservation), [key]: value } }));
  }

  async function decide(reservation: RoomReservation, action: "approve-payment" | "reject") {
    setNotice("");
    const form = formFor(reservation);
    const amount = Number(form.amount);
    if (action === "approve-payment" && (!amount || amount <= 0)) {
      setNotice("Enter a deposit/payment amount greater than 0 before approving payment.");
      return;
    }
    try {
      await apiFetch(`/landlord/reservations/${reservation.id}/${action}`, {
        method: "POST",
        body: JSON.stringify({ amount: action === "approve-payment" ? amount : undefined, note: form.note || (action === "approve-payment" ? "Approved to pay deposit." : "Reservation request rejected.") })
      });
      setNotice(action === "approve-payment" ? "Room seeker can now pay the deposit." : "Reservation request rejected.");
      await load();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Reservation action failed");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Reservations</p>
          <h1>Room reservation requests</h1>
          <p>Review room seekers first. Deposit payment is only enabled after you approve the request.</p>
        </div>
        <div className="header-stat">
          <strong>{reservations.length}</strong>
          <span>requests</span>
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}
      {!loading && !error ? (
        <div className="panel table-panel">
          {reservations.length === 0 ? <div className="data-state">No reservation requests yet.</div> : null}
          {reservations.map((reservation) => (
            <article className="request-card" key={reservation.id}>
              <div className="card-topline">
                <StatusPill value={reservation.status} />
                <span>{reservation.reservation_code}</span>
              </div>
              <h2>{reservation.full_name ?? "Room seeker"}</h2>
              <p>{reservation.room_number ?? "Room"} at {reservation.property_name ?? "property"}</p>
              <dl className="detail-grid">
                <div><dt>Phone</dt><dd>{reservation.phone ?? "Not provided"}</dd></div>
                <div><dt>Email</dt><dd>{reservation.email ?? "Not provided"}</dd></div>
                <div><dt>Deposit</dt><dd>M{Number(reservation.reservation_amount).toLocaleString()}</dd></div>
                <div><dt>Expiry</dt><dd>{reservation.reservation_expiry ? new Date(reservation.reservation_expiry).toLocaleString() : "Not set"}</dd></div>
              </dl>
              {reservation.message ? <p>{reservation.message}</p> : null}
              {reservation.status === "pending_landlord_review" ? (
                <div className="form-panel compact-form">
                  <label>Approved payment amount<input inputMode="numeric" value={formFor(reservation).amount} onChange={(event) => updateDecision(reservation, "amount", event.target.value)} /></label>
                  <label>Decision message<input value={formFor(reservation).note} onChange={(event) => updateDecision(reservation, "note", event.target.value)} placeholder="Optional message for this room seeker" /></label>
                  <div className="button-row">
                    <button className="primary-button" type="button" onClick={() => decide(reservation, "approve-payment")}>Approve Payment</button>
                    <button className="secondary-button danger" type="button" onClick={() => decide(reservation, "reject")}>Reject</button>
                  </div>
                </div>
              ) : null}
              {reservation.status === "approved_for_payment" ? (
                <div className="button-row">
                  <p className="privacy-note">Waiting for room seeker deposit payment.</p>
                  <button className="secondary-button danger" type="button" onClick={() => decide(reservation, "reject")}>Cancel approval</button>
                </div>
              ) : null}
              {reservation.status === "payment_pending" ? <p className="privacy-note">Payment sent and waiting for verified provider webhook confirmation.</p> : null}
              {reservation.status === "confirmed" ? <p className="privacy-note">Reservation confirmed. The room is reserved and hidden from public listings.</p> : null}
              {reservation.status === "rejected" || reservation.status === "cancelled" ? <p className="privacy-note">{reservation.rejection_message ?? "Request closed."}</p> : null}
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
