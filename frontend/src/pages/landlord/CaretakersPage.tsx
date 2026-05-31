import { FormEvent, useEffect, useState } from "react";
import { apiFetch } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/DataState";
import { PasswordField } from "../../components/PasswordField";
import { StatusPill } from "../../components/StatusPill";
import type { Caretaker } from "../../types";

type CaretakerForm = {
  id?: string;
  full_name: string;
  email: string;
  phone: string;
  password: string;
  is_active: boolean;
};

const emptyForm: CaretakerForm = {
  full_name: "",
  email: "",
  phone: "",
  password: "Password123!",
  is_active: true
};

function formFromCaretaker(caretaker: Caretaker): CaretakerForm {
  return {
    id: caretaker.id,
    full_name: caretaker.full_name,
    email: caretaker.email,
    phone: caretaker.phone ?? "",
    password: "",
    is_active: caretaker.is_active
  };
}

function nullable(value: string) {
  return value.trim() ? value.trim() : null;
}

export function CaretakersPage() {
  const [caretakers, setCaretakers] = useState<Caretaker[]>([]);
  const [form, setForm] = useState<CaretakerForm>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyId, setBusyId] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      setCaretakers(await apiFetch("/caretakers") as Caretaker[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load caretakers");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function update<K extends keyof CaretakerForm>(key: K, value: CaretakerForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function saveCaretaker(event: FormEvent) {
    event.preventDefault();
    setNotice("");
    try {
      if (form.id) {
        await apiFetch(`/caretakers/${form.id}`, {
          method: "PUT",
          body: JSON.stringify({
            full_name: form.full_name,
            email: form.email,
            phone: nullable(form.phone),
            is_active: form.is_active
          })
        });
        setNotice("Caretaker updated.");
      } else {
        await apiFetch("/caretakers", {
          method: "POST",
          body: JSON.stringify({
            full_name: form.full_name,
            email: form.email,
            phone: nullable(form.phone),
            password: form.password
          })
        });
        setNotice("Caretaker account created. Share the username and temporary password securely.");
      }
      setForm(emptyForm);
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not save caretaker");
    }
  }

  async function removeCaretaker(caretaker: Caretaker) {
    setBusyId(caretaker.id);
    setNotice("");
    try {
      await apiFetch(`/caretakers/${caretaker.id}`, { method: "DELETE" });
      setNotice("Caretaker removed and account disabled.");
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not remove caretaker");
    } finally {
      setBusyId("");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Operations team</p>
          <h1>Caretakers</h1>
          <p>Create caretaker login accounts, update contact details, disable access, or remove caretakers from your landlord scope.</p>
        </div>
        <div className="header-stat">
          <strong>{caretakers.length}</strong>
          <span>caretakers</span>
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {notice ? <div className="data-state">{notice}</div> : null}

      <div className="admin-grid">
        <form className="panel form-panel" onSubmit={saveCaretaker}>
          <div>
            <p className="eyebrow">{form.id ? "Edit caretaker" : "New caretaker"}</p>
            <h2>{form.id ? form.full_name : "Create caretaker account"}</h2>
          </div>
          <label>Full name<input required value={form.full_name} onChange={(event) => update("full_name", event.target.value)} /></label>
          <div className="form-grid">
            <label>Email<input required type="email" value={form.email} onChange={(event) => update("email", event.target.value)} /></label>
            <label>Phone<input value={form.phone} onChange={(event) => update("phone", event.target.value)} /></label>
          </div>
          {!form.id ? <label>Temporary password<PasswordField required minLength={8} value={form.password} onChange={(value) => update("password", value)} /></label> : null}
          {form.id ? (
            <label className="inline-check"><input type="checkbox" checked={form.is_active} onChange={(event) => update("is_active", event.target.checked)} /> Account active</label>
          ) : null}
          <div className="review-actions">
            <button className="primary-button" type="submit">{form.id ? "Save caretaker" : "Create caretaker"}</button>
            {form.id ? <button type="button" onClick={() => setForm(emptyForm)}>Cancel edit</button> : null}
          </div>
        </form>

        <div className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Assigned accounts</p>
              <h2>Caretaker list</h2>
            </div>
          </div>
          <div className="list-stack compact-list">
            {caretakers.length === 0 && !loading ? <div className="data-state">No caretakers yet.</div> : null}
            {caretakers.map((caretaker) => (
              <article className="row-item rich" key={caretaker.id}>
                <div>
                  <div className="card-topline">
                    <StatusPill value={caretaker.is_active ? "active" : "disabled"} />
                    <span>{caretaker.username ?? "No username"}</span>
                  </div>
                  <strong>{caretaker.full_name}</strong>
                  <p>{caretaker.email}{caretaker.phone ? ` - ${caretaker.phone}` : ""}</p>
                </div>
                <div className="review-actions">
                  <button type="button" onClick={() => setForm(formFromCaretaker(caretaker))}>Edit</button>
                  <button type="button" disabled={busyId === caretaker.id} onClick={() => removeCaretaker(caretaker)}>Delete</button>
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
