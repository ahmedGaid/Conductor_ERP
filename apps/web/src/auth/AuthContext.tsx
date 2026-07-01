import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { apiFetch, getToken, refreshAccess, setToken } from "../api/client";

interface LoginResult {
  access?: string;
  twofa_required?: boolean;
}

interface AuthState {
  isAuthenticated: boolean;
  /** True while the boot-time session restore (refresh cookie → access token) is in flight. */
  restoring: boolean;
  login: (username: string, password: string, otp?: string) => Promise<LoginResult>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getToken());
  const [restoring, setRestoring] = useState(!getToken());

  // The access token lives only in memory, so a reload starts signed out; the HttpOnly refresh
  // cookie (set at login) silently restores the session before the router redirects to /login.
  useEffect(() => {
    if (!restoring) return;
    let cancelled = false;
    refreshAccess().then(() => {
      if (cancelled) return;
      setTokenState(getToken());
      setRestoring(false);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      isAuthenticated: Boolean(token),
      restoring,
      async login(username, password, otp) {
        const result = await apiFetch<LoginResult>("/identity/login", {
          method: "POST",
          body: JSON.stringify({ username, password, otp_code: otp ?? "" }),
        });
        if (result.access) {
          setToken(result.access);
          setTokenState(result.access);
        }
        return result;
      },
      logout() {
        // Blacklist the refresh token and clear its cookie server-side; local state drops now.
        void apiFetch("/identity/logout", { method: "POST" }).catch(() => undefined);
        setToken(null);
        setTokenState(null);
      },
    }),
    [token, restoring],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
