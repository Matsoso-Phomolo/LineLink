import { FormEvent, useState } from "react";
import { apiFetch } from "../../api/client";

type PreferredResponseMethod =
  | "email"
  | "phone_call"
  | "sms"
  | "whatsapp";

type LandlordRequestForm = {
  business_name: string;
  full_name: string;
  email: string;
  phone: string;
  address: string;
  preferred_response_method: PreferredResponseMethod;
  response_contact_value: string;
  emergency_contact: string;
  message: string;
};

const initialForm: LandlordRequestForm = {
  business_name: "",
  full_name: "",
  email: "",
  phone: "",
  address: "",
  preferred_response_method: "email",
  response_contact_value: "",
  emergency_contact: "",
  message: "",
};

export function LandlordRequestPage() {
  const [form, setForm] = useState(initialForm);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

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
    setSubmitting(true);

    try {
      await apiFetch("/landlords/requests", {
        method: "POST",
        body: JSON.stringify(form),
      });

      setForm(initialForm);

      setStatus(
        "Landlord request submitted successfully. RentaLink administrators will review your request and may send a verification form using your selected response method."
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
            <span>LL</span>

            <div>
              <strong>RentaLink</strong>
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
              RentaLink verifies landlord identity,
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

          <a
            className="secondary-button"
            href="#/login"
          >
            Back to sign in
          </a>
        </div>

        <form
          className="auth-card application-form-card"
          onSubmit={submit}
        >
          <div>
            <p className="eyebrow">
              Landlord request
            </p>

            <h2>Join RentaLink</h2>
          </div>

          <label>
            Business / line-house name

            <input
              required
              value={form.business_name}
              onChange={(event) =>
                updateField(
                  "business_name",
                  event.target.value
                )
              }
              placeholder="Matsoso Ten House Holdings"
            />
          </label>

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
              placeholder="Tell us about your rental operations and why you want to join RentaLink."
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
      </section>
    </main>
  );
}
