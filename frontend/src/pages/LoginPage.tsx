import { FormEvent, useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { getDefaultDashboardForRole } from "../auth/roleDashboardMap";
import { useAuth } from "../auth/AuthContext";
import { HeroPhotoCarousel } from "../components/HeroPhotoCarousel";

export function LoginPage() {
  const { user, login, verifyTwoFactor } = useAuth();
  const navigate = useNavigate();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [twoFactorChallenge, setTwoFactorChallenge] = useState<{
    id: string;
    channel?: string | null;
    demoOtp?: string | null;
  } | null>(null);
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    return (
      <Navigate
        to={getDefaultDashboardForRole(user.role)}
        replace
      />
    );
  }

  function navigateAfterLogin(currentUser: any) {
    const destination = getDefaultDashboardForRole(currentUser.role, {
      districtId: currentUser.district_id,
      tenantId: currentUser.tenant_id,
    });

    navigate(destination);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const currentUser = await login(identifier, password);

      if ("requires_2fa" in currentUser) {
        setTwoFactorChallenge({
          id: currentUser.challenge_id,
          channel: currentUser.channel,
          demoOtp: currentUser.demo_otp,
        });
        return;
      }

      if (currentUser.must_change_password) {
        navigate("/change-password");
      } else {
        navigateAfterLogin(currentUser);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTwoFactorSubmit(event: FormEvent) {
    event.preventDefault();

    if (!twoFactorChallenge) return;

    setSubmitting(true);
    setError("");

    try {
      const currentUser = await verifyTwoFactor(twoFactorChallenge.id, otp);

      if (currentUser.must_change_password) {
        navigate("/change-password");
      } else {
        navigateAfterLogin(currentUser);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to verify security code"
      );
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
            <span>RL</span>

            <div>
              <strong>Rentalink</strong>
              <small>Smart rental governance platform</small>
            </div>
          </div>

          <div className="hero-copy">
            <p className="eyebrow">Rentalink</p>

            <h1>
              Manage rentals remotely. Monitor payments intelligently.
            </h1>

            <p>
              A national smart rental governance platform for landlords,
              caretakers, tenants, district admins, and rental operations teams.
            </p>
          </div>

          <div className="hero-photo-grid">
            <HeroPhotoCarousel />
          </div>
        </div>

        <form
          className="login-card"
          onSubmit={twoFactorChallenge ? handleTwoFactorSubmit : handleSubmit}
        >
          <div>
            <p className="eyebrow">Secure access</p>
            <h2>{twoFactorChallenge ? "Verify code" : "Sign in"}</h2>
          </div>

          {twoFactorChallenge ? (
            <>
              <p className="privacy-note">
                Enter the security code sent by{" "}
                {twoFactorChallenge.channel ?? "email"}.
                {twoFactorChallenge.demoOtp
                  ? ` Demo code: ${twoFactorChallenge.demoOtp}`
                  : ""}
              </p>

              <label>
                Security code
                <input
                  required
                  inputMode="numeric"
                  value={otp}
                  onChange={(event) => setOtp(event.target.value)}
                  placeholder="000000"
                />
              </label>
            </>
          ) : (
            <>
              <label>
                Username / ID number
                <input
                  id="login-identifier"
                  required
                  value={identifier}
                  onChange={(event) => setIdentifier(event.target.value)}
                  autoComplete="username"
                  placeholder="RL-LND-000001"
                />
              </label>

              <div className="field-group">
                <label htmlFor="login-password">Password</label>

                <div className="password-field">
                  <input
                    id="login-password"
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                  />

                  <button
                    type="button"
                    aria-label={
                      showPassword ? "Hide password" : "Show password"
                    }
                    onClick={() => setShowPassword((value) => !value)}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </div>
            </>
          )}

          {error ? <div className="form-error">{error}</div> : null}

          <button
            type="submit"
            className="primary-button"
            disabled={submitting}
          >
            {submitting
              ? twoFactorChallenge
                ? "Verifying..."
                : "Signing in..."
              : twoFactorChallenge
              ? "Verify and continue"
              : "Sign in"}
          </button>

          {twoFactorChallenge ? (
            <button
              className="text-button"
              type="button"
              onClick={() => {
                setTwoFactorChallenge(null);
                setOtp("");
              }}
            >
              Back to sign in
            </button>
          ) : (
            <>
              <a className="text-button" href="#/forgot-password">
                Forgot password?
              </a>

              <a className="secondary-button" href="#/rooms">
                Find vacant rooms
              </a>

              <a className="secondary-button" href="#/landlord-request">
                Landlord request
              </a>
            </>
          )}
        </form>
      </section>

      <section
        className="public-footer-card"
        aria-label="Rentalink public contacts"
      >
        <div className="footer-compact-row">
          <p className="footer-signature">
            © 2026 P Matsoso •{" "}
            <a href="mailto:phomolomatsoso@gmail.com">
              phomolomatsoso@gmail.com
            </a>{" "}
            • 57260714/63355656
          </p>

          <button
            className="tiny-outline-button"
            type="button"
            onClick={() => setShowAdminModal(true)}
          >
            About Admin
          </button>
        </div>
      </section>

      {showAdminModal ? (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={() => setShowAdminModal(false)}
        >
          <section
            className="admin-profile-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="admin-profile-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button
              className="modal-close"
              type="button"
              aria-label="Close admin profile"
              onClick={() => setShowAdminModal(false)}
            >
              Close
            </button>

            <img
              src="/hero/admin/admin-photo.jpeg"
              alt="Phomolo Matsoso, Rentalink founder and system administrator"
            />

            <p className="eyebrow">Founder & System Administrator</p>

            <h2 id="admin-profile-title">Phomolo Matsoso</h2>

            <p>• Full-Stack Developer • SOC AI Systems Builder</p>

            <div className="review-actions">
              <a
                className="primary-button"
                href="https://matsoso-portfolio.vercel.app"
                target="_blank"
                rel="noreferrer"
              >
                Portfolio
              </a>

              <a
                className="secondary-button dark-action"
                href="https://wa.me/26657260714"
                target="_blank"
                rel="noreferrer"
              >
                WhatsApp
              </a>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
