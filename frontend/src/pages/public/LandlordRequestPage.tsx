import { FormEvent, useState } from "react";
import { apiFetch } from "../../api/client";

type LandlordRequestForm = {
  business_name: string;
  full_name: string;
  email: string;
  phone: number;
  address: string;
  village_location: string;
  national_id: string;
  number_of_properties: string;
  number_of_rooms: number;
  emergency_contact: string;
  message: string;
};

const initialForm: LandlordRequestForm = {
  business_name: "",
  full_name: "",
  email: "",
  phone: "",
  address: "",
  village_location: "",
  national_id: "",
  number_of_properties: "",
  number_of_rooms: "",
  emergency_contact: "",
  message: ""
};

export function LandlordRequestPage() {
  const [form, setForm] = useState(initialForm);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function updateField<K extends keyof LandlordRequestForm>(key: K, value: LandlordRequestForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setStatus("");
    setSubmitting(true);

    try {
      await apiFetch("/landlords/requests", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          number_of_properties: form.number_of_properties ? Number(form.number_of_properties) : null,
          number_of_rooms: form.number_of_rooms ? Number(form.number_of_rooms) : null
        })
      });
      setForm(initialForm);
      setStatus("Request submitted. The LineLink admin will review your details and contact you.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to submit landlord request");
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
              <strong>LineLink</strong>
              <small>Landlord onboarding</small>
            </div>
          </div>
          <div>
            <p className="eyebrow">Verified landlords only</p>
            <h1>Request access to manage your line-house professionally.</h1>
            <p>
              LineLink reviews landlord identity, line-house ownership, location, and operating details before accounts can publish rooms publicly.
            </p>
          </div>
          <div className="privacy-note">
            After submission, the admin may request selfie, ownership proof, utility bill, and lease or ownership documents before approval.
          </div>
          <a className="secondary-button" href="#/login">Back to sign in</a>
        </div>

        <form className="auth-card application-form-card" onSubmit={submit}>
          <div>
            <p className="eyebrow">Landlord request</p>
            <h2>Join LineLink</h2>
          </div>
          <label>
            Business / line name
            <input required value={form.business_name} onChange={(event) => updateField("business_name", event.target.value)} placeholder="Matsoso Holdings" />
          </label>
          <label>
            Full names
            <input required value={form.full_name} onChange={(event) => updateField("full_name", event.target.value)} placeholder="PHOMOLO MATSOSO" />
          </label>
          <div className="form-grid">
            <label>
              Email
              <input required type="email" value={form.email} onChange={(event) => updateField("email", event.target.value)} placeholder="you@example.com" />
            </label>
            <label>
              Phone
              <input required value={form.phone} onChange={(event) => updateField("phone", event.target.value)} placeholder="+266..." />
            </label>
          </div>
          <label>
            Physical address
            <input required value={form.address} onChange={(event) => updateField("address", event.target.value)} placeholder="Roma, Lesotho" />
          </label>
          <div className="form-grid">
            <label>
              Village / location
              <input required value={form.village_location} onChange={(event) => updateField("village_location", event.target.value)} placeholder="Mafikeng" />
            </label>
            <label>
              National ID
              <input required value={form.national_id} onChange={(event) => updateField("national_id", event.target.value)} />
            </label>
          </div>
          <div className="form-grid">
            <label>
              Number of properties
              <input min="1" type="number" value={form.number_of_properties} onChange={(event) => updateField("number_of_properties", event.target.value)} />
            </label>
            <label>
              Number of rooms
              <input min="1" type="number" value={form.number_of_rooms} onChange={(event) => updateField("number_of_rooms", event.target.value)} />
            </label>
          </div>
          <label>
            Emergency contact
            <input value={form.emergency_contact} onChange={(event) => updateField("emergency_contact", event.target.value)} placeholder="Name and phone number" />
          </label>
          <label>
            Message
            <textarea value={form.message} onChange={(event) => updateField("message", event.target.value)} placeholder="Tell us about your line-house, location, and verification documents available." />
          </label>
          {error ? <div className="form-error">{error}</div> : null}
          {status ? <div className="form-success">{status}</div> : null}
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting ? "Submitting..." : "Submit landlord request"}
          </button>
        </form>
      </section>
    </main>
  );
}
