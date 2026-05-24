import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function ChangePasswordPage() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [notice, setNotice] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    await apiFetch("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });
    await refreshUser();
    setNotice("Password changed.");
    navigate(user?.role === "tenant" ? "/tenant" : user?.role === "admin" ? "/admin" : "/landlord");
  }

  return (
    <main className="login-page">
      <form className="login-card standalone-card" onSubmit={submit}>
        <div>
          <p className="eyebrow">Security</p>
          <h2>Change password</h2>
          <p>Temporary passwords must be changed before using the dashboard.</p>
        </div>
        <label>Current password<div className="password-field"><input required type={showPassword ? "text" : "password"} value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /><button type="button" onClick={() => setShowPassword((value) => !value)}>{showPassword ? "Hide" : "Show"}</button></div></label>
        <label>New password<div className="password-field"><input required minLength={8} type={showPassword ? "text" : "password"} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /><button type="button" onClick={() => setShowPassword((value) => !value)}>{showPassword ? "Hide" : "Show"}</button></div></label>
        <button className="primary-button" type="submit">Change password</button>
        {notice ? <div className="data-state">{notice}</div> : null}
      </form>
    </main>
  );
}
