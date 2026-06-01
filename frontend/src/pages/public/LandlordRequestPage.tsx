import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";

type PreferredResponseMethod =
  | "email"
  | "phone_call"
  | "sms"
  | "whatsapp";

type LandlordRequestForm = {
  full_name: string;
  email: string;
  phone: string;
  address: string;
  preferred_response_method: PreferredResponseMethod;
  response_contact_value: string;
  emergency_contact: string;
  message: string;
};

type District = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  rollout_stage: string;
  description: string | null;
};

type LandlordRequestPageProps = {
  returnTo?: string;
  returnLabel?: string;
};

const initialForm: LandlordRequestForm = {
  full_name: "",
  email: "",
  phone: "",
  address: "",
  preferred_response_method: "email",
  response_contact_value: "",
  emergency_contact: "",
  message: "",
};

export function LandlordRequestPage({
  returnTo,
  returnLabel = "Return to dashboard"
}: LandlordRequestPageProps = {}) {
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [districts, setDistricts] = useState<District[]>([]);
  const [selectedDistrict, setSelectedDistrict] = useState<District | null>(null);
  const [loadingDistricts, setLoadingDistricts] = useState(true);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    async function loadDistricts() {
      setLoadingDistricts(true);
      setError("");

      try {
        const districtItems = (await apiFetch("/districts/active")) as District[];
        setDistricts(districtItems);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load active districts");
      } finally {
        setLoadingDistricts(false);
      }
    }

    loadDistricts();
  }, []);

  function updateField<K extends keyof LandlordRequestForm>(
    key: K,
    value: LandlordRequestForm[K]
  ) {
    setForm((current) => ({
      ...current,
      [key]: value,
    }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();

    setError("");
    setStatus("");

    if (!selectedDistrict) {
      setError("Select your district before submitting a landlord request.");
      return;
    }

    setSubmitting(true);

    try {
      await apiFetch("/landlords/requests", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          district_id: selectedDistrict.id,
        }),
      });

      setForm(initialForm);
      setSelectedDistrict(null);

      setStatus(
        "Landlord request submitted successfully. Rentalink administrators will review your request and may send a verification form using your selected response method."
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to submit landlord request"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="center-page public-request-page">
      <section className="auth-shell public-request-shell">
        <div className="auth-copy">
          <div className="brand-mark light">
            <span>RL</span>

            <div>
              <strong>Rentalink</strong>
              <small>Landlord onboarding</small>
            </div>
          </div>

          <div>
            <p className="eyebrow">
              Verified landlords only
            </p>

            <h1>
              Request access to manage your rental properties professionally.
            </h1>

            <p>
              Rentalink verifies landlord identity,
              ownership legitimacy, district location,
              and operational information before
              granting landlord platform access.
            </p>
          </div>

          <div className="privacy-note">
            After submitting this request,
            administrators may send a secure
            verification form requesting:
            <br />
            • Selfie verification
            <br />
            • National ID
            <br />
            • Utility bill
            <br />
            • Ownership documents
            <br />
            • Property details
          </div>

          {returnTo ? (
            <button
              className="secondary-button"
              type="button"
              onClick={() => navigate(returnTo)}
            >
              {returnLabel}
            </button>
          ) : (
            <a
              className="secondary-button"
              href="#/login"
            >
              Back to sign in
            </a>
          )}
        </div>

        <div className="auth-card application-form-card">
          <div>
            <p className="eyebrow">
              Landlord request
            </p>

            <h2>
              {selectedDistrict ? "Join Rentalink" : "Select your district"}
            </h2>
            <p>
              Select your district first so your request is routed to the correct Rentalink District Administration team.
            </p>
          </div>

          {loadingDistricts ? <LoadingState /> : null}
          {!loadingDistricts && error && !selectedDistrict ? <ErrorState message={error} /> : null}

          {!loadingDistricts && !selectedDistrict ? (
            <div className="panel compact-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">District rollout</p>
                  <h3>Choose active district</h3>
                </div>
                <StatusPill value={`${districts.length}_active`} />
              </div>

              {districts.length > 0 ? (
                <>
                  <div className="amenities compact">
                    {districts.map((district) => (
                      <button
                        className="chip-button"
                        type="button"
                        key={district.id}
                        onClick={() => {
                          setSelectedDistrict(district);
                          setError("");
                          setStatus("");
                        }}
                      >
                        {district.name}
                      </button>
                    ))}
                  </div>

                  <div className="data-state compact-state">
                    Only active districts are shown. Locked districts remain hidden until Rentalink officially rolls out there.
                  </div>
                </>
              ) : (
                <div className="data-state">No active districts are available yet. Please check again later.</div>
              )}
            </div>
          ) : null}

          {selectedDistrict ? (
            <form onSubmit={submit}>
              <div className="panel compact-panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Selected district</p>
                    <h3>{selectedDistrict.name}</h3>
                  </div>

                  <button className="secondary-button" type="button" onClick={() => setSelectedDistrict(null)}>
                    Change district
                  </button>
                </div>
              </div>

              <label>
                Full names

                <input
                  required
                  value={form.full_name}
                  onChange={(event) =>
                    updateField(
                      "full_name",
                      event.target.value
                    )
                  }
                  placeholder="PHOMOLO MATSOSO"
                />
              </label>

              <div className="form-grid">
                <label>
                  Email

                  <input
                    required
                    type="email"
                    value={form.email}
                    onChange={(event) =>
                      updateField(
                        "email",
                        event.target.value
                      )
                    }
                    placeholder="you@example.com"
                  />
                </label>

                <label>
                  Phone

                  <input
                    required
                    value={form.phone}
                    onChange={(event) =>
                      updateField(
                        "phone",
                        event.target.value
                      )
                    }
                    placeholder="+266..."
                  />
                </label>
              </div>

              <label>
                Personal physical address

                <input
                  required
                  value={form.address}
                  onChange={(event) =>
                    updateField(
                      "address",
                      event.target.value
                    )
                  }
                  placeholder="Roma, Maseru, Lesotho"
                />
              </label>

              <div className="form-grid">
                <label>
                  Preferred response method

                  <select
                    value={form.preferred_response_method}
                    onChange={(event) =>
                      updateField(
                        "preferred_response_method",
                        event.target
                          .value as PreferredResponseMethod
                      )
                    }
                  >
                    <option value="email">
                      Email
                    </option>

                    <option value="phone_call">
                      Phone call
                    </option>

                    <option value="sms">
                      SMS
                    </option>

                    <option value="whatsapp">
                      WhatsApp
                    </option>
                  </select>
                </label>

                <label>
                  Response contact value

                  <input
                    required
                    value={form.response_contact_value}
                    onChange={(event) =>
                      updateField(
                        "response_contact_value",
                        event.target.value
                      )
                    }
                    placeholder="Email or phone number"
                  />
                </label>
              </div>

              <label>
                Emergency contact

                <input
                  value={form.emergency_contact}
                  onChange={(event) =>
                    updateField(
                      "emergency_contact",
                      event.target.value
                    )
                  }
                  placeholder="Name and phone number"
                />
              </label>

              <label>
                Message

                <textarea
                  value={form.message}
                  onChange={(event) =>
                    updateField(
                      "message",
                      event.target.value
                    )
                  }
                  placeholder="Tell us about your rental operations and why you want to join Rentalink."
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

              <button
                className="primary-button"
                type="submit"
                disabled={submitting}
              >
                {submitting
                  ? "Submitting..."
                  : "Submit landlord request"}
              </button>
            </form>
          ) : null}
        </div>
      </section>
    </main>
  );
}
