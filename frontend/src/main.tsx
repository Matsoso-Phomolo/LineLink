import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { tokenStorage } from "./auth/tokenStorage";
import { AppErrorBoundary } from "./components/AppErrorBoundary";
import { AppRoutes } from "./routes/AppRoutes";
import "./styles/global.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Rentalink root element was not found.");
}

try {
  if (new URLSearchParams(window.location.search).has("resetSession")) {
    tokenStorage.remove();
  }

  createRoot(rootElement).render(
    <AppErrorBoundary>
      <HashRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </HashRouter>
    </AppErrorBoundary>
  );
} catch (error) {
  console.error("Rentalink failed to start", error);

  rootElement.innerHTML = `
    <main class="center-page">
      <section class="auth-card">
        <p class="eyebrow">Rentalink</p>
        <h1>Rentalink could not start</h1>
        <p>Please refresh the page. If this continues, check browser storage permissions or contact support.</p>
      </section>
    </main>
  `;
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js")
      .then((registration) => {
        console.log("Rentalink service worker registered");

        registration.onupdatefound = () => {
          const installingWorker = registration.installing;

          if (!installingWorker) return;

          installingWorker.onstatechange = () => {
            if (
              installingWorker.state === "installed" &&
              navigator.serviceWorker.controller
            ) {
              alert(
                "A new version of Rentalink is available. Refresh the app to update."
              );
            }
          };
        };
      })
      .catch((error) => {
        console.error("Service worker registration failed:", error);
      });
  });
}
