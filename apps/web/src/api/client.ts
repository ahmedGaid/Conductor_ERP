// Minimal fetch wrapper for the Django API.
// - Prefixes /api, attaches the JWT bearer, and unwraps the {data} / {error} envelope.
// - Vite proxies /api -> http://localhost:8000 in dev (see vite.config.ts).

const TOKEN_KEY = "erp.token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface ErrorEnvelope {
  error?: { message?: unknown; code?: string };
}

interface DataEnvelope<T> {
  data: T;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`/api${path}`, { ...init, headers });

  if (res.status === 204) return undefined as T;

  let body: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!res.ok) {
    if (res.status === 401) setToken(null);
    const env = body as ErrorEnvelope;
    const msg =
      typeof env?.error?.message === "string"
        ? env.error.message
        : `Request failed (${res.status})`;
    throw new ApiError(msg, res.status, env?.error?.code);
  }

  return (body as DataEnvelope<T>).data;
}
