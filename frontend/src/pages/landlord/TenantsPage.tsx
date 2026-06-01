import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { StatusPill } from "../../components/StatusPill";
import { TenantProfileFields, tenantTypeFromCategory, type TenantCategory, type TenantProfileForm } from "../../components/TenantProfileFields";
import type { Room, Tenant } from "../../types";

type TenantForm = TenantProfileForm & {
  id?: string;
  full_name: string;
  gender: string;
  phone: string;
  email: string;
  national_id: string;
  passport_number: string;
  next_of_kin_name: string;
  next_of_kin_phone: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  lease_start_date: string;
  lease_end_date: string;
  room_id: string;
};

const emptyTenant: TenantForm = {
  full_name: "",
  gender: "",
  phone: "",
  email: "",
  national_id: "",
  passport_number: "",
  tenant_category: "worker",
  tenant_subtype: "employed",
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
  next_of_kin_name: "",
  next_of_kin_phone: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  lease_start_date: new Date().toISOString().slice(0, 10),
  lease_end_date: "",
  room_id: ""
};

function nullable(value: string) {
  return value.trim() ? value.trim() : null;
}

function assignedRoomLabel(tenant: Tenant) {
  const source = tenant as any;
  return source.room_number ?? source.assigned_room ?? source.room?.room_number ?? "No active room shown";
}

function leaseStatus(tenant: Tenant) {
  if (tenant.tenant_status === "disabled" || tenant.tenant_status === "moved_out") {
    return "Ended";
  }

  if (tenant.lease_end_date && new Date(tenant.lease_end_date) < new Date()) {
    return "Expired";
  }

  return tenant.lease_start_date ? "Active" : "Not started";
}

type TenantsPageProps = {
  mode?: "list" | "form";
};

export function TenantsPage({ mode = "list" }: TenantsPageProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [form, setForm] = useState<TenantForm>(emptyTenant);
  const [selectedTenantId, setSelectedTenantId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyId, setBusyId] = useState("");
  const editTenantId = searchParams.get("edit");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [tenantItems, roomItems] = await Promise.all([
        apiFetch("/tenants") as Promise<Tenant[]>,
        apiFetch("/rooms") as Promise<Room[]>
      ]);
      setTenants(tenantItems);
      setRooms(roomItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load tenants");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (mode !== "form" || !editTenantId || tenants.length === 0) {
      return;
    }

    const tenant = tenants.find((item) => item.id === editTenantId);
    if (!tenant) {
      return;
    }

    setForm({
      ...emptyTenant,
      id: tenant.id,
      full_name: tenant.full_name,
      gender: tenant.gender ?? "",
      phone: tenant.phone,
      email: tenant.email ?? "",
      national_id: tenant.national_id ?? "",
      passport_number: tenant.passport_number ?? "",
      tenant_category: (tenant.tenant_category as TenantCategory) ?? (tenant.tenant_type === "student" ? "student" : "worker"),
      tenant_subtype: tenant.tenant_subtype ?? (tenant.tenant_type === "student" ? "tertiary" : "employed"),
      institution_name: tenant.institution_name ?? "",
      student_id: (tenant as any).student_number ?? "",
      sponsor_or_guardian_name: tenant.sponsor_or_guardian_name ?? "",
      employer_or_business_name: tenant.employer_or_business_name ?? "",
      occupation: tenant.occupation ?? "",
      work_location: tenant.work_location ?? "",
      number_of_occupants: tenant.number_of_occupants ? String(tenant.number_of_occupants) : "",
      children_count: tenant.children_count ? String(tenant.children_count) : "",
      parking_required: tenant.parking_required === true ? "yes" : tenant.parking_required === false ? "no" : "",
      funding_source: tenant.funding_source ?? "",
      guarantor_name: tenant.guarantor_name ?? "",
      additional_notes: tenant.additional_notes ?? "",
      next_of_kin_name: tenant.next_of_kin_name ?? "",
      next_of_kin_phone: tenant.next_of_kin_phone ?? "",
      emergency_contact_name: tenant.emergency_contact_name ?? "",
      emergency_contact_phone: tenant.emergency_contact_phone ?? "",
      lease_start_date: tenant.lease_start_date ?? "",
      lease_end_date: tenant.lease_end_date ?? "",
      room_id: ""
    });
  }, [editTenantId, mode, tenants]);

  const vacantRooms = useMemo(() => rooms.filter((room) => room.status === "vacant"), [rooms]);

  function update<K extends keyof TenantForm>(key: K, value: TenantForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function saveTenant(event: FormEvent) {
    event.preventDefault();
    setNotice("");
    try {
      if (form.id) {
        await apiFetch(`/tenants/${form.id}`, {
          method: "PUT",
          body: JSON.stringify({
            full_name: form.full_name,
            gender: nullable(form.gender),
            phone: form.phone,
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
            next_of_kin_name: nullable(form.next_of_kin_name),
            next_of_kin_phone: nullable(form.next_of_kin_phone),
            emergency_contact_name: nullable(form.emergency_contact_name),
            emergency_contact_phone: nullable(form.emergency_contact_phone),
            lease_start_date: nullable(form.lease_start_date),
            lease_end_date: nullable(form.lease_end_date)
          })
        });
        setNotice("Tenant updated.");
      } else {
        const result = await apiFetch("/tenants/accounts", {
          method: "POST",
          body: JSON.stringify({
            full_name: form.full_name,
            gender: nullable(form.gender),
            phone: form.phone,
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
            next_of_kin_name: nullable(form.next_of_kin_name),
            next_of_kin_phone: nullable(form.next_of_kin_phone),
            emergency_contact_name: nullable(form.emergency_contact_name),
            emergency_contact_phone: nullable(form.emergency_contact_phone),
            lease_start_date: nullable(form.lease_start_date),
            lease_end_date: nullable(form.lease_end_date),
            room_id: nullable(form.room_id)
          })
        }) as { username: string; temporary_password: string };
        setNotice(`Tenant account created. Username: ${result.username}. Temporary password: ${result.temporary_password}`);
      }
      setForm(emptyTenant);
      await loadData();
      navigate("/landlord/tenants");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not save tenant");
    }
  }

  async function disableTenant(tenant: Tenant) {
    setBusyId(tenant.id);
    setNotice("");
    try {
      await apiFetch(`/tenants/${tenant.id}`, { method: "DELETE" });
      setNotice("Tenant disabled.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not disable tenant");
    } finally {
      setBusyId("");
    }
  }

  if (mode === "form") {
    return (
      <section className="page-stack">
        <div className="page-header">
          <div>
            <p className="eyebrow">Tenant management</p>
            <h1>{form.id ? "Edit Tenant" : "Add Tenant"}</h1>
            <p>{form.id ? "Update tenant profile details." : "Create a tenant account and assign it to one of your vacant rooms."}</p>
          </div>
          <button className="secondary-button" type="button" onClick={() => navigate("/landlord/tenants")}>
            Back to tenants
          </button>
        </div>
        {loading ? <LoadingState /> : null}
        {error ? <ErrorState message={error} /> : null}
        {notice ? <div className="data-state">{notice}</div> : null}

        {!loading && !error ? (
          <form className="panel form-panel" onSubmit={saveTenant}>
            <div><p className="eyebrow">{form.id ? "Edit tenant" : "Create tenant"}</p><h2>{form.id ? form.full_name : "Register tenant account"}</h2></div>
            <div className="form-grid">
              <label>Full names<input required value={form.full_name} onChange={(event) => update("full_name", event.target.value)} /></label>
              <label>Gender<input value={form.gender} onChange={(event) => update("gender", event.target.value)} /></label>
            </div>
            <div className="form-grid">
              <label>Phone<input required value={form.phone} onChange={(event) => update("phone", event.target.value)} /></label>
              <label>Email<input type="email" value={form.email} onChange={(event) => update("email", event.target.value)} /></label>
            </div>
            <div className="form-grid">
              <label>National ID<input value={form.national_id} onChange={(event) => update("national_id", event.target.value)} /></label>
              <label>Passport<input value={form.passport_number} onChange={(event) => update("passport_number", event.target.value)} /></label>
            </div>
            <TenantProfileFields form={form} update={update} />
            <div className="form-grid">
              <label>Next of kin<input value={form.next_of_kin_name} onChange={(event) => update("next_of_kin_name", event.target.value)} /></label>
              <label>Next of kin phone<input value={form.next_of_kin_phone} onChange={(event) => update("next_of_kin_phone", event.target.value)} /></label>
            </div>
            <div className="form-grid">
              <label>Emergency contact<input value={form.emergency_contact_name} onChange={(event) => update("emergency_contact_name", event.target.value)} /></label>
              <label>Emergency phone<input value={form.emergency_contact_phone} onChange={(event) => update("emergency_contact_phone", event.target.value)} /></label>
            </div>
            <div className="form-grid">
              <label>Lease start<input type="date" value={form.lease_start_date} onChange={(event) => update("lease_start_date", event.target.value)} /></label>
              <label>Lease end<input type="date" value={form.lease_end_date} onChange={(event) => update("lease_end_date", event.target.value)} /></label>
            </div>
            {!form.id ? <label>Assign vacant room<select value={form.room_id} onChange={(event) => update("room_id", event.target.value)}><option value="">Choose vacant room</option>{vacantRooms.map((room) => <option key={room.id} value={room.id}>{room.room_number} - M{Number(room.rent_price).toLocaleString()}</option>)}</select></label> : null}
            <div className="review-actions">
              <button className="primary-button" type="submit">{form.id ? "Save tenant" : "Create tenant account"}</button>
              <button type="button" onClick={() => navigate("/landlord/tenants")}>Cancel</button>
            </div>
          </form>
        ) : null}
      </section>
    );
  }

  const selectedTenant = tenants.find((tenant) => tenant.id === selectedTenantId) ?? null;

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Tenant management</p>
          <h1>Tenants</h1>
          <p>Review current tenant records, assigned rooms, categories, lease status, and account status.</p>
        </div>
        <button className="primary-button" type="button" onClick={() => navigate("/landlord/tenants/new")}>
          Add Tenant
        </button>
        <div className="header-stat"><strong>{tenants.length}</strong><span>tenants</span></div>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}

      <div className="list-stack">
        {!loading && tenants.length === 0 ? (
          <div className="data-state">No tenants have been added yet.</div>
        ) : null}

        {tenants.map((tenant) => (
          <article className="row-item rich" key={tenant.id}>
            <div>
              <div className="card-topline"><StatusPill value={tenant.tenant_status ?? "active"} /><span>{(tenant.tenant_category ?? tenant.tenant_type).replace("_", " ")}</span></div>
              <strong>{tenant.full_name}</strong>
              <p>{tenant.phone}{tenant.email ? ` - ${tenant.email}` : ""}</p>
              <small>Room: {assignedRoomLabel(tenant)} | Lease: {leaseStatus(tenant)}</small>
            </div>
            <div className="review-actions">
              <button type="button" onClick={() => setSelectedTenantId(selectedTenantId === tenant.id ? "" : tenant.id)}>View</button>
              <button type="button" onClick={() => navigate(`/landlord/tenants/new?edit=${tenant.id}`)}>Edit</button>
              <button type="button" disabled={busyId === tenant.id} onClick={() => disableTenant(tenant)}>Disable</button>
            </div>
            {selectedTenant?.id === tenant.id ? (
              <div className="data-state compact-state">
                <strong>{tenant.full_name}</strong>
                <p>Category: {tenant.tenant_category ?? tenant.tenant_type}. Status: {tenant.tenant_status ?? "active"}. Assigned room: {assignedRoomLabel(tenant)}. Lease status: {leaseStatus(tenant)}.</p>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
