import { useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export function PWAPrompt() {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);

  const [visible, setVisible] = useState(false);
  const [autoPrompted, setAutoPrompted] = useState(false);

  function isStandalone() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true
    );
  }

  useEffect(() => {
    function handler(event: Event) {
      if (isStandalone()) return;

      event.preventDefault();

      setDeferredPrompt(event as BeforeInstallPromptEvent);

      setVisible(true);
    }

    window.addEventListener("beforeinstallprompt", handler);

    function handleInstalled() {
      setVisible(false);
      setDeferredPrompt(null);
    }

    window.addEventListener("appinstalled", handleInstalled);

    return () => {
      window.removeEventListener(
        "beforeinstallprompt",
        handler
      );
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  useEffect(() => {
    if (!visible || !deferredPrompt || autoPrompted) return;

    const timer = window.setTimeout(() => {
      setAutoPrompted(true);
      install();
    }, 900);

    return () => window.clearTimeout(timer);
  }, [visible, deferredPrompt, autoPrompted]);

  async function install() {
    if (!deferredPrompt) return;

    try {
      await deferredPrompt.prompt();
    } catch {
      setVisible(true);
      return;
    }

    const choice = await deferredPrompt.userChoice;

    if (choice.outcome === "accepted") {
      setVisible(false);
      setDeferredPrompt(null);
    }
  }

  if (!visible) {
    return null;
  }

  return (
    <div className="pwa-install-overlay" role="dialog" aria-modal="true">
      <section className="pwa-install-dialog">
        <div className="pwa-install-icon">RL</div>

        <div>
          <p className="eyebrow">Install app</p>
          <h2>Install Rentalink</h2>
          <p>
            Add Rentalink to your phone home screen for faster access,
            offline fallback, and an app-like rental operations experience.
          </p>
        </div>

        <div className="pwa-install-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => setVisible(false)}
          >
            Cancel
          </button>

          <button
            type="button"
            className="primary-button"
            onClick={install}
          >
            Install
          </button>
        </div>
      </section>
    </div>
  );
}
