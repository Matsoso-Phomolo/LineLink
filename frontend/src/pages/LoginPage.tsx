import { FormEvent, useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { HeroPhotoCarousel } from "../components/HeroPhotoCarousel";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showAdminModal, setShowAdminModal] = useState(false);
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

  useEffect(() => {
    if (!showAdminModal) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setShowAdminModal(false);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [showAdminModal]);

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
            <input required value={identifier} onChange={(event) => setIdentifier(event.target.value)} autoComplete="username" placeholder="LL-LND-000001" />
          </label>
          <label>
            Password
            <div className="password-field">
              <input required value={password} onChange={(event) => setPassword(event.target.value)} type={showPassword ? "text" : "password"} autoComplete="current-password" />
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
      <section className="public-footer-card" aria-label="LineLink public contacts">
        <div className="footer-heading">
          <div>
            <p className="eyebrow">Contact</p>
            <h2>Built and operated by PHOMOLO MATSOSO</h2>
          </div>
          <button className="tiny-outline-button" type="button" onClick={() => setShowAdminModal(true)}>About Admin</button>
        </div>
        <div className="contact-card-grid">
          <a className="contact-card" href="mailto:phomolomatsoso@gmail.com">
            <span>Email</span>
            <strong>phomolomatsoso@gmail.com</strong>
          </a>
          <a className="contact-card" href="https://wa.me/26657260714" target="_blank" rel="noreferrer">
            <span>WhatsApp</span>
            <strong>57260714 / 63355656</strong>
          </a>
          <a className="contact-card" href="https://github.com/Matsoso-Phomolo" target="_blank" rel="noreferrer">
            <span>GitHub</span>
            <strong>@Matsoso-Phomolo</strong>
          </a>
          <a className="contact-card" href="https://www.linkedin.com/" target="_blank" rel="noreferrer">
            <span>LinkedIn</span>
            <strong>PHOMOLO MATSOSO</strong>
          </a>
        </div>
        <p className="footer-signature">© 2026 PHOMOLO MATSOSO • Backend Developer • Full-Stack Builder • SOC AI Systems</p>
      </section>
      {showAdminModal ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setShowAdminModal(false)}>
          <section className="admin-profile-modal" role="dialog" aria-modal="true" aria-labelledby="admin-profile-title" onMouseDown={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" aria-label="Close admin profile" onClick={() => setShowAdminModal(false)}>Close</button>
            <img src="/hero/admin/admin-photo.jpeg" alt="PHOMOLO MATSOSO, LineLink founder and system administrator" />
            <p className="eyebrow">Founder & System Administrator</p>
            <h2 id="admin-profile-title">PHOMOLO MATSOSO</h2>
            <p>Backend Developer • Full-Stack Builder • SOC AI Systems Engineer</p>
            <div className="admin-contact-list">
              <a href="mailto:phomolomatsoso@gmail.com">phomolomatsoso@gmail.com</a>
              <a href="https://wa.me/26657260714" target="_blank" rel="noreferrer">57260714</a>
              <a href="https://wa.me/26663355656" target="_blank" rel="noreferrer">63355656</a>
            </div>
            <div className="review-actions">
              <a className="secondary-button" href="https://github.com/Matsoso-Phomolo" target="_blank" rel="noreferrer">GitHub</a>
              <a className="secondary-button" href="https://wa.me/26657260714" target="_blank" rel="noreferrer">WhatsApp</a>
              <a className="primary-button" href="mailto:phomolomatsoso@gmail.com">Email</a>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
