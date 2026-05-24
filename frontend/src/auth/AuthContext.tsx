import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiFetch, loginRequest } from "../api/client";
import type { User } from "../types";

type AuthContextValue = {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("linelink_token"));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(token));

  async function refreshUser() {
    if (!localStorage.getItem("linelink_token")) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const currentUser = await apiFetch("/auth/me");
      setUser(currentUser);
    } catch {
      localStorage.removeItem("linelink_token");
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
    localStorage.setItem("linelink_token", response.access_token);
    setToken(response.access_token);
    const currentUser = await apiFetch("/auth/me");
    setUser(currentUser);
    return currentUser;
  }

  function logout() {
    localStorage.removeItem("linelink_token");
    setToken(null);
    setUser(null);
  }

  const value = useMemo(() => ({ user, token, loading, login, logout, refreshUser }), [user, token, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
