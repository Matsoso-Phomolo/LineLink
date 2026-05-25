import { FormEvent, useState } from "react";
import { apiFetch } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { StatusPill } from "../components/StatusPill";

export function SecurityPage() {
  const { user, refreshUser } = useAuth();
  const [channel, setChannel] = useState(user?.preferred_2fa_channel ?? "email");
  const [notice, setNotice] = useState("");

  async function enable(event: FormEvent) {
    event.preventDefault();
    setNotice("");
    try {
      await apiFetch("/auth/2fa/setup", {
        method: "POST",
        body: JSON.stringify({ channel, enabled: true })
      });
      await refreshUser();
      setNotice("Two-factor authentication updated.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not update two-factor authentication");
    }
  }

  async function disable() {
    setNotice("");
    try {
      await apiFetch("/auth/2fa/disable", { method: "POST" });
      await refreshUser();
      setNotice("Two-factor authentication disabled.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Could not disable two-factor authentication");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Security</p>
          <h1>Two-factor authentication</h1>
          <p>Protect sensitive LineLink access with an email, SMS, or WhatsApp OTP scaffold.</p>
        </div>
        <StatusPill value={user?.two_factor_enabled || user?.two_factor_required ? "enabled" : "disabled"} />
      </div>
      {user?.role === "admin" && !(user.two_factor_enabled || user.two_factor_required) ? (
        <div className="form-error">Admin accounts require two-factor authentication before production use.</div>
      ) : null}
      {notice ? <div className="data-state">{notice}</div> : null}
      <form className="panel form-panel" onSubmit={enable}>
        <label>Preferred channel<select value={channel} onChange={(event) => setChannel(event.target.value)}>
          <option value="email">Email OTP</option>
          <option value="sms">SMS OTP scaffold</option>
          <option value="whatsapp">WhatsApp OTP scaffold</option>
        </select></label>
        <button className="primary-button" type="submit">Enable / update 2FA</button>
        <button type="button" disabled={user?.role === "admin"} onClick={disable}>Disable 2FA</button>
      </form>
    </section>
  );
}
