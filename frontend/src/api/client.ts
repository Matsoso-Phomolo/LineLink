import { tokenStorage } from "../auth/tokenStorage";

const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim();

export const API_BASE_URL = configuredApiBase || "http://127.0.0.1:8001";

async function responseError(response: Response) {
  const text = await response.text();
  try {
    const parsed = JSON.parse(text) as { detail?: unknown; message?: unknown };
    const detail = parsed.detail ?? parsed.message;
    if (typeof detail === "string") return new Error(detail);
    if (Array.isArray(detail)) return new Error("Please check the form fields and try again.");
  } catch {
    if (text.trim()) return new Error(text);
  }
  return new Error(`Request failed with status ${response.status}`);
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = tokenStorage.get();
  const isFormData = options.body instanceof FormData;
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers
      }
    });
  } catch {
    throw new Error("Could not reach Rentalink backend. Please check your connection or backend deployment.");
  }

  if (!response.ok) {
    throw await responseError(response);
  }

  const text = await response.text();

  if (!text.trim()) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new Error(
      "The API returned a non-JSON response. Please check the backend URL configuration."
    );
  }
}

export type LoginResponse = {
  access_token?: string | null;
  token_type?: string;
  requires_2fa?: boolean;
  challenge_id?: string | null;
  channel?: string | null;
  demo_otp?: string | null;
};

export async function loginRequest(identifier: string, password: string) {
  const body = new URLSearchParams();
  body.set("username", identifier);
  body.set("password", password);
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 20000);

  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
      signal: controller.signal
    });

    if (!response.ok) {
      throw await responseError(response);
    }

    return response.json() as Promise<LoginResponse>;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Login is taking too long. Please try again in a moment.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}
