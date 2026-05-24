import { tokenStorage } from "../auth/tokenStorage";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8001";

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
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers
    }
  });

  if (!response.ok) {
    throw await responseError(response);
  }

  return response.json();
}

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

    return response.json() as Promise<{ access_token: string; token_type: string }>;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Login is taking too long. Please try again in a moment.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}
