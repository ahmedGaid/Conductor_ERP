import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { apiFetch, getToken, refreshAccess, setToken } from "../api/client";
import { getMe } from "../api/identity";

interface LoginResult {
  access?: string;
  twofa_required?: boolean;
}

interface AuthState {
  isAuthenticated: boolean;
  /** True while the boot-time session restore (refresh cookie → access token) is in flight. */
  restoring: boolean;
  /**
   * The signed-in user's role names (from `/identity/me`), null until loaded. Fine-grained
   * permission codes aren't exposed to the frontend yet — this is the coarse client-side gate
   * (e.g. menu items with `permission: "admin"`) until a real permission-code endpoint lands.
   */
  roles: string[] | null;
  hasRole: (role: string) => boolean;
  login: (username: string, password: string, otp?: string) => Promise<LoginResult>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getToken());
  const [restoring, setRestoring] = useState(!getToken());
  const [roles, setRoles] = useState<string[] | null>(null);

  // Load the signed-in user's roles once authenticated. Best-effort — a failed fetch just leaves
  // permission-gated menu items hidden (fail closed) rather than blocking the app.
  useEffect(() => {
    if (!token) {
      setRoles(null);
      return;
    }
    let alive = true;
    getMe()
      .then((me) => {
        if (alive) setRoles(me.roles);
      })
      .catch(() => {
        if (alive) setRoles(null);
      });
    return () => {
      alive = false;
    };
  }, [token]);

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
      roles,
      hasRole: (role) => roles?.includes(role) ?? false,
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
    [token, restoring, roles],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
