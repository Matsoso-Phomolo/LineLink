import { useEffect, useState } from "react";

import { subscribeToPushNotifications } from "../utils/pushSubscription";

const API_BASE =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:9000";

export default function PushNotificationPrompt() {
  const [supported, setSupported] = useState(false);
  const [permission, setPermission] =
    useState<NotificationPermission>("default");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if ("Notification" in window && "serviceWorker" in navigator) {
      setSupported(true);
      setPermission(Notification.permission);
    }
  }, []);

  async function saveSubscription(subscription: PushSubscription) {
    const token =
      localStorage.getItem("access_token") ||
      localStorage.getItem("token");

    const response = await fetch(`${API_BASE}/push-subscriptions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(subscription),
    });

    if (!response.ok) {
      throw new Error("Failed to save push subscription.");
    }
  }

  async function requestPermission() {
    if (!supported) return;

    setSaving(true);
    setError("");

    try {
      const result = await Notification.requestPermission();
      setPermission(result);

      if (result !== "granted") {
        setError("Notifications were not enabled.");
        return;
      }

      const subscription = await subscribeToPushNotifications();
      await saveSubscription(subscription);

      setSaved(true);

      new Notification("Rentalink alerts enabled", {
        body: "You are ready to receive rental intelligence alerts.",
        icon: "/icons/icon-192.png",
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to enable notifications."
      );
    } finally {
      setSaving(false);
    }
  }

  if (!supported) {
    return null;
  }

  if (permission === "granted" && saved) {
    return (
      <div className="rounded-2xl border border-green-800 bg-green-500/10 p-5">
        <p className="text-sm font-semibold text-green-300">
          Rentalink alerts are enabled
        </p>

        <p className="mt-2 text-sm text-gray-300">
          This device is registered for operational intelligence notifications.
        </p>
      </div>
    );
  }

  if (permission === "granted" && !saved) {
    return (
      <div className="rounded-2xl border border-yellow-800 bg-yellow-500/10 p-5">
        <p className="text-sm font-semibold text-yellow-300">
          Notifications allowed
        </p>

        <p className="mt-2 text-sm text-gray-300">
          Register this device to receive Rentalink operational alerts.
        </p>

        {error ? (
          <p className="mt-3 text-sm text-red-400">
            {error}
          </p>
        ) : null}

        <button
          type="button"
          onClick={requestPermission}
          disabled={saving}
          className="mt-4 rounded-xl border border-yellow-700 bg-yellow-500 px-4 py-2 text-sm font-semibold text-black disabled:opacity-60"
        >
          {saving ? "Registering..." : "Register Device"}
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-cyan-800 bg-cyan-500/10 p-5">
      <p className="text-sm font-semibold text-cyan-300">
        Enable Rentalink Alerts
      </p>

      <p className="mt-2 text-sm text-gray-300">
        Allow browser notifications so Rentalink can notify you about overdue
        rent, payment risk, critical tenant alerts and operational events.
      </p>

      {error ? (
        <p className="mt-3 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      <button
        type="button"
        onClick={requestPermission}
        disabled={saving}
        className="mt-4 rounded-xl border border-cyan-700 bg-cyan-500 px-4 py-2 text-sm font-semibold text-black disabled:opacity-60"
      >
        {saving ? "Enabling..." : "Enable Notifications"}
      </button>
    </div>
  );
}
