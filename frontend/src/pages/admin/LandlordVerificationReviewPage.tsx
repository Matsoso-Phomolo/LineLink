import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";

type PropertyVerification = {
  id: string;
  property_name: string;
  village_location: string;
  address: string;
  total_rooms: number;
  single_rooms: number;
  double_rooms: number;
  single_room_prefix: string;
  double_room_prefix: string;
  starting_room_number: number;
  single_room_rent: number | null;
  double_room_rent: number | null;
};

type VerificationRequest = {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  address: string | null;
  status: string;
  national_id: string | null;
  admin_note: string | null;
  ai_recommendation?: string | null;
  ai_confidence_score?: number | null;
  ai_summary?: string | null;
  ai_risk_flags?: string | null;
  created_at: string;
  properties: PropertyVerification[];
};

export function LandlordVerificationReviewPage() {
  const [requests, setRequests] = useState<VerificationRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] =
    useState<VerificationRequest | null>(null);

  const [adminNote, setAdminNote] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  async function loadRequests() {
    setLoading(true);

    try {
      const data = await apiFetch("/landlords/requests");

      const verificationRequests = data.filter(
        (request: VerificationRequest) =>
          request.status === "verification_submitted" ||
          request.status === "ai_reviewed"
      );

      setRequests(verificationRequests);

      if (
        verificationRequests.length > 0 &&
        !selectedRequest
      ) {
        setSelectedRequest(verificationRequests[0]);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load requests"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRequests();
  }, []);

  async function approveVerification() {
    if (!selectedRequest) return;

    setActionLoading(true);
    setError("");
    setStatus("");

    try {
      await apiFetch(
        `/landlords/requests/${selectedRequest.id}/approve-verification`,
        {
          method: "POST",
          body: JSON.stringify({
            admin_note: adminNote,
          }),
        }
      );

      setStatus("Verification approved successfully.");

      await loadRequests();

      setSelectedRequest(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to approve verification"
      );
    } finally {
      setActionLoading(false);
    }
  }

  async function rejectVerification() {
    if (!selectedRequest) return;

    setActionLoading(true);
    setError("");
    setStatus("");

    try {
      await apiFetch(
        `/landlords/requests/${selectedRequest.id}/reject-verification`,
        {
          method: "POST",
          body: JSON.stringify({
            admin_note: adminNote,
          }),
        }
      );

      setStatus("Verification rejected.");

      await loadRequests();

      setSelectedRequest(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to reject verification"
      );
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <main className="dashboard-page">
      <section className="dashboard-header">
        <div>
          <p className="eyebrow">
            Verification review
          </p>

          <h1>Landlord verification requests</h1>

          <p>
            Review landlord verification submissions,
            property structures,
            room configuration,
            and pricing.
          </p>
        </div>
      </section>

      <section className="dashboard-grid two-column">
        <aside className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Queue</p>
              <h2>Verification requests</h2>
            </div>
          </div>

          {loading ? (
            <p>Loading requests...</p>
          ) : requests.length === 0 ? (
            <p>No pending verification requests.</p>
          ) : (
            <div className="stack-list">
              {requests.map((request) => (
                <button
                  key={request.id}
                  className={`list-card ${
                    selectedRequest?.id === request.id
                      ? "active"
                      : ""
                  }`}
                  onClick={() =>
                    setSelectedRequest(request)
                  }
                >
                  <strong>
                    {request.full_name}
                  </strong>

                  <small>
                    {request.email}
                  </small>

                  <span>
                    {request.properties.length} properties
                  </span>
                </button>
              ))}
            </div>
          )}
        </aside>

        <section className="panel">
          {!selectedRequest ? (
            <p>Select a verification request.</p>
          ) : (
            <>
              <div className="section-heading">
                <div>
                  <p className="eyebrow">
                    Verification details
                  </p>

                  <h2>
                    {selectedRequest.full_name}
                  </h2>
                </div>
              </div>

              <div className="details-grid">
                <div>
                  <strong>Email</strong>
                  <p>{selectedRequest.email}</p>
                </div>

                <div>
                  <strong>Phone</strong>
                  <p>
                    {selectedRequest.phone || "-"}
                  </p>
                </div>

                <div>
                  <strong>Address</strong>
                  <p>
                    {selectedRequest.address || "-"}
                  </p>
                </div>

                <div>
                  <strong>Status</strong>
                  <p>{selectedRequest.status}</p>
                </div>
              </div>

              <div className="section-heading">
                <div>
                  <p className="eyebrow">
                    Properties
                  </p>

                  <h2>
                    Submitted properties
                  </h2>
                </div>
              </div>

              <section className="panel nested-panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">AI verification assistant</p>
                    <h3>
                      {selectedRequest.ai_recommendation
                        ? selectedRequest.ai_recommendation.replace("_", " ")
                        : "Awaiting review"}
                    </h3>
                  </div>
                  {selectedRequest.ai_confidence_score != null ? (
                    <span className="status-pill">
                      {Math.round(Number(selectedRequest.ai_confidence_score) * 100)}%
                      confidence
                    </span>
                  ) : null}
                </div>

                <p>
                  {selectedRequest.ai_summary ||
                    "The assistant will summarize completeness, risk, and recommended action after verification is submitted."}
                </p>

                {selectedRequest.ai_risk_flags ? (
                  <pre className="code-note">
                    {selectedRequest.ai_risk_flags}
                  </pre>
                ) : null}
              </section>

              <div className="stack-list">
                {selectedRequest.properties.map(
                  (property) => (
                    <section
                      className="panel nested-panel"
                      key={property.id}
                    >
                      <div className="section-heading">
                        <div>
                          <p className="eyebrow">
                            Property
                          </p>

                          <h3>
                            {property.property_name}
                          </h3>
                        </div>
                      </div>

                      <div className="details-grid">
                        <div>
                          <strong>Village</strong>
                          <p>
                            {
                              property.village_location
                            }
                          </p>
                        </div>

                        <div>
                          <strong>Address</strong>
                          <p>
                            {property.address}
                          </p>
                        </div>

                        <div>
                          <strong>
                            Total rooms
                          </strong>
                          <p>
                            {
                              property.total_rooms
                            }
                          </p>
                        </div>

                        <div>
                          <strong>
                            Single rooms
                          </strong>
                          <p>
                            {
                              property.single_rooms
                            }
                          </p>
                        </div>

                        <div>
                          <strong>
                            Double rooms
                          </strong>
                          <p>
                            {
                              property.double_rooms
                            }
                          </p>
                        </div>

                        <div>
                          <strong>
                            Starting number
                          </strong>
                          <p>
                            {
                              property.starting_room_number
                            }
                          </p>
                        </div>

                        <div>
                          <strong>
                            Single prefix
                          </strong>
                          <p>
                            {
                              property.single_room_prefix
                            }
                          </p>
                        </div>

                        <div>
                          <strong>
                            Double prefix
                          </strong>
                          <p>
                            {
                              property.double_room_prefix
                            }
                          </p>
                        </div>

                        <div>
                          <strong>
                            Single room rent
                          </strong>
                          <p>
                            M
                            {property.single_room_rent ??
                              0}
                          </p>
                        </div>

                        <div>
                          <strong>
                            Double room rent
                          </strong>
                          <p>
                            M
                            {property.double_room_rent ??
                              0}
                          </p>
                        </div>
                      </div>

                      <div className="subscription-preview">
                        <strong>
                          Estimated subscription
                        </strong>

                        <p>
                          {property.total_rooms <=
                          15
                            ? "M50"
                            : property.total_rooms <
                              30
                            ? "M75"
                            : "M100"}
                        </p>
                      </div>
                    </section>
                  )
                )}
              </div>

              <label>
                Admin note

                <textarea
                  value={adminNote}
                  onChange={(event) =>
                    setAdminNote(
                      event.target.value
                    )
                  }
                  placeholder="Verification notes or rejection reason"
                />
              </label>

              {error ? (
                <div className="form-error">
                  {error}
                </div>
              ) : null}

              {status ? (
                <div className="form-success">
                  {status}
                </div>
              ) : null}

              <div className="action-row">
                <button
                  className="danger-button"
                  type="button"
                  disabled={actionLoading}
                  onClick={rejectVerification}
                >
                  Reject verification
                </button>

                <button
                  className="primary-button"
                  type="button"
                  disabled={actionLoading}
                  onClick={approveVerification}
                >
                  Approve verification
                </button>
              </div>
            </>
          )}
        </section>
      </section>
    </main>
  );
}
