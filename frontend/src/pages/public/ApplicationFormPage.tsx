import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import { TenantProfileFields, tenantTypeFromCategory, type TenantCategory, type TenantProfileForm } from "../../components/TenantProfileFields";
import type { TenantApplication } from "../../types";

type FullApplicationForm = TenantProfileForm & {
  full_name: string;
  gender: string;
  phone: string;
  alternative_phone: string;
  email: string;
  national_id: string;
  passport_number: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  preferred_move_in_date: string;
  message: string;
};

const emptyForm: FullApplicationForm = {
  full_name: "",
  gender: "",
  phone: "",
  alternative_phone: "",
  email: "",
  national_id: "",
  passport_number: "",
  tenant_category: "student",
  tenant_subtype: "tertiary",
  institution_name: "",
  student_id: "",
  sponsor_or_guardian_name: "",
  employer_or_business_name: "",
  occupation: "",
  work_location: "",
  number_of_occupants: "",
  children_count: "",
  parking_required: "",
  funding_source: "",
  guarantor_name: "",
  additional_notes: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  preferred_move_in_date: "",
  message: ""
};

function nullable(value: string) {
  return value.trim() ? value.trim() : null;
}

export function ApplicationFormPage() {
  const { token } = useParams();
  const [application, setApplication] = useState<TenantApplication | null>(null);
  const [form, setForm] = useState<FullApplicationForm>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) return;
    apiFetch(`/public/applications/${token}`)
      .then((item: TenantApplication) => {
        setApplication(item);
        setForm({
          full_name: item.full_name ?? "",
          gender: item.gender ?? "",
          phone: item.phone ?? "",
          alternative_phone: item.alternative_phone ?? "",
          email: item.email ?? "",
          national_id: item.national_id ?? "",
          passport_number: item.passport_number ?? "",
          tenant_category: (item.tenant_category as TenantCategory) ?? (item.tenant_type === "student" ? "student" : "worker"),
          tenant_subtype: item.tenant_subtype ?? (item.tenant_type === "student" ? "tertiary" : "employed"),
          institution_name: item.institution_name ?? item.institution ?? "",
          student_id: item.student_number ?? "",
          sponsor_or_guardian_name: item.sponsor_or_guardian_name ?? "",
          employer_or_business_name: item.employer_or_business_name ?? "",
          occupation: item.occupation ?? "",
          work_location: item.work_location ?? "",
          number_of_occupants: item.number_of_occupants ? String(item.number_of_occupants) : "",
          children_count: item.children_count ? String(item.children_count) : "",
          parking_required: item.parking_required === true ? "yes" : item.parking_required === false ? "no" : "",
          funding_source: item.funding_source ?? "",
          guarantor_name: item.guarantor_name ?? "",
          additional_notes: item.additional_notes ?? "",
          emergency_contact_name: item.emergency_contact_name ?? "",
          emergency_contact_phone: item.emergency_contact_phone ?? "",
          preferred_move_in_date: item.preferred_move_in_date ?? "",
          message: item.message ?? ""
        });
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Application link could not be loaded"))
      .finally(() => setLoading(false));
  }, [token]);

  function update<K extends keyof FullApplicationForm>(key: K, value: FullApplicationForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    if (form.tenant_category === "student" && !form.institution_name.trim()) {
      setNotice("Student applications require institution name.");
      return;
    }
    if (form.tenant_category === "worker" && !form.occupation.trim()) {
      setNotice("Worker applications require occupation.");
      return;
    }
    if (form.tenant_category === "family" && !form.number_of_occupants.trim()) {
      setNotice("Family applications require number of occupants.");
      return;
    }
    setSubmitting(true);
    setNotice("");
    try {
      const updated = await apiFetch(`/public/applications/${token}`, {
        method: "POST",
        body: JSON.stringify({
          full_name: form.full_name,
          gender: nullable(form.gender),
          phone: form.phone,
          alternative_phone: nullable(form.alternative_phone),
          email: nullable(form.email),
          national_id: nullable(form.national_id),
          passport_number: nullable(form.passport_number),
          tenant_type: tenantTypeFromCategory(form.tenant_category),
          tenant_category: form.tenant_category,
          tenant_subtype: form.tenant_subtype,
          student_number: nullable(form.student_id),
          institution: nullable(form.institution_name),
          institution_name: nullable(form.institution_name),
          sponsor_or_guardian_name: nullable(form.sponsor_or_guardian_name),
          occupation: nullable(form.occupation),
          employer_or_business_name: nullable(form.employer_or_business_name),
          work_location: nullable(form.work_location),
          number_of_occupants: form.number_of_occupants ? Number(form.number_of_occupants) : null,
          children_count: form.children_count ? Number(form.children_count) : null,
          parking_required: form.parking_required ? form.parking_required === "yes" : null,
          funding_source: nullable(form.funding_source),
          guarantor_name: nullable(form.guarantor_name),
          additional_notes: nullable(form.additional_notes),
          emergency_contact_name: form.emergency_contact_name,
          emergency_contact_phone: form.emergency_contact_phone,
          preferred_move_in_date: nullable(form.preferred_move_in_date),
          message: nullable(form.message)
        })
      }) as TenantApplication;
      setApplication(updated);
      setNotice("Application submitted. The landlord/caretaker will review and contact you.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Application could not be submitted");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="center-page public-apply-page">
      <div className="auth-shell">
        <div className="auth-copy">
          <div className="brand-mark">
            <span>RL</span>
            <div>
              <strong>Rentalink</strong>
              <small>Secure application</small>
            </div>
          </div>
          <h1>Complete your room application</h1>
          <p>Your details stay attached to the exact landlord, property, and room you requested.</p>
          {application ? (
            <div className="mini-card">
              <StatusPill value={application.status} />
              <strong>{application.full_name}</strong>
              <span>{application.phone}</span>
            </div>
          ) : null}
        </div>
        <form className="auth-card application-form-card" onSubmit={submit}>
          {loading ? <LoadingState /> : null}
          {error ? <ErrorState message={error} /> : null}
          {!loading && !error ? (
            <>
              <h2>Personal details</h2>
              <label>Full names<input required value={form.full_name} onChange={(event) => update("full_name", event.target.value)} /></label>
              <div className="form-grid">
                <label>Gender<input value={form.gender} onChange={(event) => update("gender", event.target.value)} /></label>
                <label>Phone<input required value={form.phone} onChange={(event) => update("phone", event.target.value)} /></label>
              </div>
              <div className="form-grid">
                <label>Alternative phone<input value={form.alternative_phone} onChange={(event) => update("alternative_phone", event.target.value)} /></label>
                <label>Email<input type="email" value={form.email} onChange={(event) => update("email", event.target.value)} /></label>
              </div>
              <div className="form-grid">
                <label>National ID<input value={form.national_id} onChange={(event) => update("national_id", event.target.value)} /></label>
                <label>Passport number<input value={form.passport_number} onChange={(event) => update("passport_number", event.target.value)} /></label>
              </div>
              <TenantProfileFields form={form} update={update} />
              <label>Preferred move-in<input type="date" value={form.preferred_move_in_date} onChange={(event) => update("preferred_move_in_date", event.target.value)} /></label>
              <div className="form-grid">
                <label>Emergency contact name<input required value={form.emergency_contact_name} onChange={(event) => update("emergency_contact_name", event.target.value)} /></label>
                <label>Emergency contact phone<input required value={form.emergency_contact_phone} onChange={(event) => update("emergency_contact_phone", event.target.value)} /></label>
              </div>
              <label>Message<textarea value={form.message} onChange={(event) => update("message", event.target.value)} /></label>
              <button className="primary-button" disabled={submitting || application?.status === "submitted"} type="submit">
                {submitting ? "Submitting..." : application?.status === "submitted" ? "Application submitted" : "Submit application"}
              </button>
              {notice ? <div className="data-state">{notice}</div> : null}
            </>
          ) : null}
        </form>
      </div>
    </section>
  );
}
