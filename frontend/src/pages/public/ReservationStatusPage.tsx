import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import type { RoomReservation } from "../../types";

export function ReservationStatusPage() {
  const { reservationId } = useParams();
  const [reservation, setReservation] = useState<RoomReservation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [paymentForm, setPaymentForm] = useState({ method: "mopay_mpesa", payer_phone: "" });

  useEffect(() => {
    if (!reservationId) return;
    apiFetch(`/room-reservations/${reservationId}`)
      .then(setReservation)
      .catch((err) => setError(err instanceof Error ? err.message : "Reservation could not be loaded"))
      .finally(() => setLoading(false));
  }, [reservationId]);

  async function submitPayment(event: FormEvent) {
    event.preventDefault();
    if (!reservation) return;
    setNotice("");
    try {
      await apiFetch(`/room-reservations/${reservation.id}/pay`, {
        method: "POST",
        body: JSON.stringify({
          amount: reservation.reservation_amount,
          method: paymentForm.method,
          payer_phone: paymentForm.payer_phone
        })
      });
      setNotice("Payment request sent. Confirm on your phone. Rentalink will confirm the reservation only after the verified payment callback.");
      const refreshed = await apiFetch(`/room-reservations/${reservation.id}`) as RoomReservation;
      setReservation(refreshed);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Payment request could not be sent");
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!reservation) return <ErrorState message="Reservation not found" />;

  const canPay = reservation.status === "approved_for_payment";

  return (
    <section className="page-stack">
      <div className="public-topbar">
        <div className="brand-mark light">
          <span>RL</span>
          <div>
            <strong>Rentalink</strong>
            <small>Reservation</small>
          </div>
        </div>
        <a href="#/rooms">Back to Room Finder</a>
      </div>

      <div className="page-header">
        <div>
          <p className="eyebrow">Room reservation</p>
          <h1>{reservation.room_number ?? reservation.reservation_code}</h1>
          <p>{reservation.property_name ?? "Property"} - deposit/reservation amount M{Number(reservation.reservation_amount).toLocaleString()}</p>
        </div>
        <div className="header-stat">
          <strong>{reservation.reservation_code}</strong>
          <span>{reservation.status.replaceAll("_", " ")}</span>
        </div>
      </div>

      <div className="panel">
        <StatusPill value={reservation.status} />
        {reservation.status === "pending_landlord_review" ? <p>Waiting for landlord review. Payment is not enabled yet.</p> : null}
        {reservation.status === "approved_for_payment" ? <p>Approved: you may now pay the deposit/reservation amount.</p> : null}
        {reservation.status === "payment_pending" ? <p>Payment is pending provider confirmation. Do not pay again unless the landlord asks you to retry.</p> : null}
        {reservation.status === "confirmed" ? <p>Your room reservation is confirmed and a receipt has been generated.</p> : null}
        {reservation.status === "rejected" ? <p>This request was not accepted. You may continue searching for other available rooms.</p> : null}
      </div>

      {canPay ? (
        <form className="panel form-panel payment-request-panel" onSubmit={submitPayment}>
          <h2>Pay deposit</h2>
          <label>Method<select value={paymentForm.method} onChange={(event) => setPaymentForm((current) => ({ ...current, method: event.target.value }))}>
            <option value="mopay_mpesa">MoPay M-Pesa</option>
            <option value="mopay_ecocash">MoPay EcoCash</option>
            <option value="bank_transfer">Bank transfer</option>
          </select></label>
          <label>Wallet phone number<input required={paymentForm.method !== "bank_transfer"} value={paymentForm.payer_phone} onChange={(event) => setPaymentForm((current) => ({ ...current, payer_phone: event.target.value }))} /></label>
          <button className="primary-button" type="submit">Pay Deposit</button>
          <p className="privacy-note">Rentalink never asks for or stores wallet PINs. Confirm payment only through your official wallet prompt, USSD, or banking channel.</p>
        </form>
      ) : null}
      {notice ? <div className="data-state">{notice}</div> : null}
    </section>
  );
}
