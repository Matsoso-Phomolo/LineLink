import { useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export function PWAPrompt() {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);

  const [visible, setVisible] = useState(false);

  useEffect(() => {
    function handler(event: Event) {
      event.preventDefault();

      setDeferredPrompt(event as BeforeInstallPromptEvent);

      setVisible(true);
    }

    window.addEventListener("beforeinstallprompt", handler);

    return () => {
      window.removeEventListener(
        "beforeinstallprompt",
        handler
      );
    };
  }, []);

  async function install() {
    if (!deferredPrompt) return;

    await deferredPrompt.prompt();

    const choice = await deferredPrompt.userChoice;

    if (choice.outcome === "accepted") {
      setVisible(false);
    }
  }

  if (!visible) {
    return null;
  }

  return (
    <div className="pwa-install-banner">
      <div>
        <strong>Install Rentalink</strong>

        <p>
          Add Rentalink to your home screen for a faster
          app-like experience.
        </p>
      </div>

      <button
        type="button"
        onClick={install}
      >
        Install
      </button>
    </div>
  );
}
