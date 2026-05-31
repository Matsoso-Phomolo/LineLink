import { FormEvent, useState } from "react";
import { apiFetch } from "../api/client";
import { PasswordField } from "../components/PasswordField";

export function ForgotPasswordPage() {
  const [identifier, setIdentifier] = useState("");
  const [channel, setChannel] = useState("email");
  const [notice, setNotice] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");

  async function requestReset(event: FormEvent) {
    event.preventDefault();
    const result = await apiFetch("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ identifier, channel })
    }) as { detail: string; reset_token_demo?: string };
    setNotice(result.detail);
    if (result.reset_token_demo) setToken(result.reset_token_demo);
  }

  async function confirmReset(event: FormEvent) {
    event.preventDefault();
    await apiFetch("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword })
    });
    setNotice("Password reset complete. You can sign in now.");
  }

  return (
    <main className="login-page">
      <section className="login-panel compact-auth">
        <div className="login-copy">
          <div className="brand-mark light landing-brand"><span>RL</span><div><strong>Rentalink</strong><small>Password recovery</small></div></div>
          <div className="hero-copy">
            <p className="eyebrow">Recovery</p>
            <h1>Reset your Rentalink access safely.</h1>
            <p>Email is active now. WhatsApp and SMS channels are scaffolded for provider integration.</p>
          </div>
        </div>
        <div className="login-card">
          <form className="form-panel" onSubmit={requestReset}>
            <h2>Request reset</h2>
            <label>Username / ID number<input required value={identifier} onChange={(event) => setIdentifier(event.target.value)} /></label>
            <label>Channel<select value={channel} onChange={(event) => setChannel(event.target.value)}>
              <option value="email">Email</option>
              <option value="whatsapp">WhatsApp later</option>
              <option value="sms">SMS later</option>
            </select></label>
            <button className="primary-button" type="submit">Send reset token</button>
          </form>
          <form className="form-panel" onSubmit={confirmReset}>
            <h2>Set new password</h2>
            <label>Reset token<input required value={token} onChange={(event) => setToken(event.target.value)} /></label>
            <label>New password<PasswordField required minLength={8} value={newPassword} onChange={setNewPassword} /></label>
            <button className="secondary-button" type="submit">Reset password</button>
          </form>
          {notice ? <div className="data-state">{notice}</div> : null}
          <a className="text-button" href="#/login">Back to sign in</a>
        </div>
      </section>
    </main>
  );
}
