import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiFetch, loginRequest } from "../api/client";
import type { User } from "../types";
import { tokenStorage } from "./tokenStorage";

type AuthContextValue = {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<User | { requires_2fa: true; challenge_id: string; channel?: string | null; demo_otp?: string | null }>;
  verifyTwoFactor: (challengeId: string, otp: string) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => tokenStorage.get());
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(token));

  async function refreshUser() {
    if (!tokenStorage.get()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const currentUser = await apiFetch("/auth/me");
      setUser(currentUser);
    } catch {
      tokenStorage.remove();
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshUser();
  }, []);

  async function login(identifier: string, password: string) {
    const response = await loginRequest(identifier, password);
    if (response.requires_2fa) {
      if (!response.challenge_id) throw new Error("Two-factor challenge was not created");
      return { requires_2fa: true, challenge_id: response.challenge_id, channel: response.channel, demo_otp: response.demo_otp };
    }
    if (!response.access_token) throw new Error("Login did not return an access token");
    tokenStorage.set(response.access_token);
    setToken(response.access_token);
    const currentUser = await apiFetch("/auth/me");
    setUser(currentUser);
    return currentUser;
  }

  async function verifyTwoFactor(challengeId: string, otp: string) {
    const response = await apiFetch("/auth/2fa/verify", {
      method: "POST",
      body: JSON.stringify({ challenge_id: challengeId, otp })
    }) as { access_token?: string | null };
    if (!response.access_token) throw new Error("Two-factor verification did not return an access token");
    tokenStorage.set(response.access_token);
    setToken(response.access_token);
    const currentUser = await apiFetch("/auth/me");
    setUser(currentUser);
    return currentUser;
  }

  function logout() {
    tokenStorage.remove();
    setToken(null);
    setUser(null);
  }

  const value = useMemo(() => ({ user, token, loading, login, verifyTwoFactor, logout, refreshUser }), [user, token, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
