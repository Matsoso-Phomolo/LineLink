import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { HeroPhotoCarousel } from "../components/HeroPhotoCarousel";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
      const currentUser = await login(identifier, password);
      if (currentUser.must_change_password) {
        navigate("/change-password");
      } else {
        navigate(currentUser.role === "tenant" ? "/tenant" : currentUser.role === "admin" ? "/admin" : "/landlord");
      }
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
          <div className="hero-photo-grid">
            <HeroPhotoCarousel title="Roma Village" folder="villages" filenames={["roma-village.jpg", "village-2.jpg", "village-3.jpg"]} />
            <HeroPhotoCarousel title="NUL Campus" folder="nul-campus" filenames={["nul-campus.jpg", "campus-2.jpg", "campus-3.jpg"]} />
            <HeroPhotoCarousel title="Student accommodation" folder="lines" filenames={["roma-accommodation.jpg", "line-2.jpg", "line-3.jpg"]} />
          </div>
        </div>
        <form className="login-card" onSubmit={handleSubmit}>
          <div>
            <p className="eyebrow">Secure access</p>
            <h2>Sign in</h2>
          </div>
          <label>
            Username / ID number
            <input value={identifier} onChange={(event) => setIdentifier(event.target.value)} autoComplete="username" placeholder="LL-LND-000001" />
          </label>
          <label>
            Password
            <div className="password-field">
              <input value={password} onChange={(event) => setPassword(event.target.value)} type={showPassword ? "text" : "password"} autoComplete="current-password" />
              <button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((value) => !value)}>
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          {error ? <div className="form-error">{error}</div> : null}
          <button type="submit" className="primary-button" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
          <a className="text-button" href="#/forgot-password">Forgot password?</a>
          <a className="secondary-button" href="#/rooms">Find vacant rooms</a>
        </form>
      </section>
    </main>
  );
}
