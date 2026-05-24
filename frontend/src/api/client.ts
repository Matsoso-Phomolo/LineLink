export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8001";

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem("linelink_token");
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
    throw new Error(await response.text());
  }

  return response.json();
}

export async function loginRequest(identifier: string, password: string) {
  const body = new URLSearchParams();
  body.set("username", identifier);
  body.set("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<{ access_token: string; token_type: string }>;
}
