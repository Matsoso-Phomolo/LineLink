import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";

type LandlordRequest = {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  address: string | null;
  preferred_response_method: string;
  response_contact_value: string;
  emergency_contact: string | null;
  message: string | null;
  status: string;
  admin_note: string | null;
  verification_url?: string | null;
  verification_token?: string | null;
  created_at: string;
};

export function LandlordRequestsPage() {
  const [requests, setRequests] = useState<LandlordRequest[]>([]);
  const [selectedRequest, setSelectedRequest] =
    useState<LandlordRequest | null>(null);

  const [adminNote, setAdminNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  async function loadRequests() {
    setLoading(true);
    setError("");

    try {
      const data = await apiFetch("/landlords/requests");

      const pendingRequests = data.filter(
        (request: LandlordRequest) =>
          request.status === "pending" ||
          request.status === "under_review"
      );

      setRequests(pendingRequests);

      if (pendingRequests.length > 0 && !selectedRequest) {
        setSelectedRequest(pendingRequests[0]);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load landlord requests"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRequests();
  }, []);

  async function requestVerification() {
    if (!selectedRequest) return;

    setActionLoading(true);
    setError("");
    setStatus("");

    try {
      const result = (await apiFetch(
        `/landlords/requests/${selectedRequest.id}/request-verification`,
        {
          method: "POST",
          body: JSON.stringify({
            admin_note: adminNote,
          }),
        }
      )) as LandlordRequest;

      setStatus(
        result.verification_url
          ? `Verification requested. Form link: ${result.verification_url}`
          : "Verification requested. The landlord can now receive the verification form link."
      );

      setAdminNote("");
      setSelectedRequest(null);

      await loadRequests();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to request verification"
      );
    } finally {
      setActionLoading(false);
    }
  }

  async function rejectRequest() {
    if (!selectedRequest) return;

    setActionLoading(true);
    setError("");
    setStatus("");

    try {
      await apiFetch(`/landlords/requests/${selectedRequest.id}/reject`, {
        method: "POST",
        body: JSON.stringify({
          admin_note: adminNote,
        }),
      });

      setStatus("Landlord request rejected.");

      setAdminNote("");
      setSelectedRequest(null);

      await loadRequests();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to reject landlord request"
      );
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <main className="dashboard-page">
      <section className="dashboard-header">
        <div>
          <p className="eyebrow">Landlord onboarding</p>
          <h1>Landlord requests</h1>
          <p>
            Review new landlord onboarding requests before sending the
            verification form.
          </p>
        </div>
      </section>

      <section className="dashboard-grid two-column">
        <aside className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Queue</p>
              <h2>New requests</h2>
            </div>
          </div>

          {loading ? (
            <p>Loading requests...</p>
          ) : requests.length === 0 ? (
            <p>No new landlord requests.</p>
          ) : (
            <div className="stack-list">
              {requests.map((request) => (
                <button
                  key={request.id}
                  className={`list-card ${
                    selectedRequest?.id === request.id ? "active" : ""
                  }`}
                  type="button"
                  onClick={() => {
                    setSelectedRequest(request);
                    setAdminNote(request.admin_note || "");
                  }}
                >
                  <strong>{request.full_name}</strong>
                  <small>{request.email}</small>
                  <span>{request.status}</span>
                </button>
              ))}
            </div>
          )}
        </aside>

        <section className="panel">
          {!selectedRequest ? (
            <p>Select a landlord request.</p>
          ) : (
            <>
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Request details</p>
                  <h2>{selectedRequest.full_name}</h2>
                </div>
              </div>

              <div className="details-grid">
                <div>
                  <strong>Email</strong>
                  <p>{selectedRequest.email}</p>
                </div>

                <div>
                  <strong>Phone</strong>
                  <p>{selectedRequest.phone || "-"}</p>
                </div>

                <div>
                  <strong>Personal address</strong>
                  <p>{selectedRequest.address || "-"}</p>
                </div>

                <div>
                  <strong>Preferred response</strong>
                  <p>{selectedRequest.preferred_response_method}</p>
                </div>

                <div>
                  <strong>Response contact</strong>
                  <p>{selectedRequest.response_contact_value}</p>
                </div>

                <div>
                  <strong>Emergency contact</strong>
                  <p>{selectedRequest.emergency_contact || "-"}</p>
                </div>

                <div>
                  <strong>Status</strong>
                  <p>{selectedRequest.status}</p>
                </div>

                <div>
                  <strong>Submitted</strong>
                  <p>
                    {new Date(selectedRequest.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="panel nested-panel">
                <strong>Message</strong>
                <p>{selectedRequest.message || "No message provided."}</p>
              </div>

              <label>
                Admin note / response message
                <textarea
                  value={adminNote}
                  onChange={(event) => setAdminNote(event.target.value)}
                  placeholder="Write verification instructions or rejection reason"
                />
              </label>

              {error ? <div className="form-error">{error}</div> : null}
              {status ? <div className="form-success">{status}</div> : null}

              <div className="action-row">
                <button
                  className="danger-button"
                  type="button"
                  disabled={actionLoading}
                  onClick={rejectRequest}
                >
                  Reject request
                </button>

                <button
                  className="primary-button"
                  type="button"
                  disabled={actionLoading}
                  onClick={requestVerification}
                >
                  Request verification
                </button>
              </div>
            </>
          )}
        </section>
      </section>
    </main>
  );
}
