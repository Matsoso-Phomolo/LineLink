import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { VacantRoomsPreview } from "../components/VacantRoomsPreview";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    return <Navigate to={user.role === "tenant" ? "/tenant" : user.role === "admin" ? "/admin" : "/landlord"} replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const currentUser = await login(email, password);
      navigate(currentUser.role === "tenant" ? "/tenant" : currentUser.role === "admin" ? "/admin" : "/landlord");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <div className="login-copy">
          <div className="brand-mark light landing-brand">
            <span>LL</span>
            <div>
              <strong>LineLink</strong>
              <small>Remote line-house management</small>
            </div>
          </div>
          <div className="hero-copy">
            <p className="eyebrow">LineLink</p>
            <h1>Manage line-houses remotely. Find vacant rooms faster.</h1>
            <p>
              A focused platform for Roma and NUL landlords, caretakers, tenants, and room seekers to manage rentals, applications, occupancy, rent, and support without walking from house to house.
            </p>
          </div>
        </div>
        <form className="login-card" onSubmit={handleSubmit}>
          <div>
            <p className="eyebrow">Secure access</p>
            <h2>Sign in</h2>
          </div>
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" />
          </label>
          <label>
            Password
            <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" />
          </label>
          {error ? <div className="form-error">{error}</div> : null}
          <button type="submit" className="primary-button" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
          <VacantRoomsPreview />
        </form>
      </section>
    </main>
  );
}
