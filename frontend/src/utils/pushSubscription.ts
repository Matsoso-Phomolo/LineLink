const PUBLIC_VAPID_KEY =
  import.meta.env.VITE_PUBLIC_VAPID_KEY || "";

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);

  const base64 = (base64String + padding)
    .replace(/-/g, "+")
    .replace(/_/g, "/");

  const rawData = window.atob(base64);

  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

export async function subscribeToPushNotifications() {
  if (!("serviceWorker" in navigator)) {
    throw new Error("Service workers are not supported.");
  }

  if (!("PushManager" in window)) {
    throw new Error("Push notifications are not supported.");
  }

  if (!PUBLIC_VAPID_KEY) {
    throw new Error("Missing VITE_PUBLIC_VAPID_KEY.");
  }

  const registration = await navigator.serviceWorker.ready;

  const existingSubscription =
    await registration.pushManager.getSubscription();

  if (existingSubscription) {
    return existingSubscription;
  }

  return registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(PUBLIC_VAPID_KEY),
  });
}
