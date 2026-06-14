import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { apiFetch, getToken, setToken } from "../api/client";

interface LoginResult {
  access?: string;
  refresh?: string;
  twofa_required?: boolean;
}

interface AuthState {
  isAuthenticated: boolean;
  login: (username: string, password: string, otp?: string) => Promise<LoginResult>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getToken());

  const value = useMemo<AuthState>(
    () => ({
      isAuthenticated: Boolean(token),
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
        setToken(null);
        setTokenState(null);
      },
    }),
    [token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
