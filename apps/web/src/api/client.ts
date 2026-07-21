// Minimal fetch wrapper for the Django API.
// - Prefixes /api, attaches the JWT bearer, and unwraps the {data} / {error} envelope.
// - On a successful write (non-GET), evicts the cached lists that write affects, so created/
//   changed records show up immediately the next time their list is viewed.
// - Vite proxies /api -> http://localhost:8000 in dev (see vite.config.ts).

import { invalidateForPath } from "../lib/cache";
import i18n from "../i18n";

// The short-lived access token lives ONLY in memory (never storage — XSS cannot read it back).
// Sessions survive reloads through the HttpOnly refresh cookie: `refreshAccess` trades it for a
// new access token on boot and transparently after a 401.
let accessToken: string | null = null;

// One-time cleanup of the pre-hardening localStorage token.
try {
  localStorage.removeItem("erp.token");
} catch {
  /* storage unavailable (private mode) — nothing to clean */
}

// The active UI language, sent as Accept-Language so the server localizes its built-in (DRF)
// validation messages to match what the user is reading. Falls back to Arabic (the app default).
function activeLanguage(): string {
  return i18n.resolvedLanguage || i18n.language || "ar";
}

export function getToken(): string | null {
  return accessToken;
}

export function setToken(token: string | null): void {
  accessToken = token;
}

// Single-flight refresh: concurrent 401s share one round-trip. The refresh token itself never
// reaches this code — the browser sends the HttpOnly cookie (scoped to /api/identity) by itself.
let refreshing: Promise<boolean> | null = null;

export function refreshAccess(): Promise<boolean> {
  refreshing ??= (async () => {
    try {
      const res = await fetch("/api/identity/token/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!res.ok) {
        setToken(null);
        return false;
      }
      const body = (await res.json()) as { access?: string };
      setToken(body.access ?? null);
      return Boolean(body.access);
    } catch {
      setToken(null);
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
    readonly data?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface ErrorEnvelope {
  error?: { message?: unknown; code?: string; data?: Record<string, unknown> };
}

interface DataEnvelope<T> {
  data: T;
}

async function authedFetch(path: string, init: RequestInit, headers: Headers): Promise<Response> {
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res = await fetch(`/api${path}`, { ...init, headers });
  // Expired access token: renew through the refresh cookie once and replay the request.
  if (res.status === 401 && (await refreshAccess())) {
    headers.set("Authorization", `Bearer ${getToken()}`);
    res = await fetch(`/api${path}`, { ...init, headers });
  }
  return res;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  headers.set("Accept-Language", activeLanguage());

  const res = await authedFetch(path, init, headers);

  const method = (init.method ?? "GET").toUpperCase();
  const mutating = method !== "GET";

  if (res.status === 204) {
    if (mutating) invalidateForPath(path);
    return undefined as T;
  }

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
    throw new ApiError(msg, res.status, env?.error?.code, env?.error?.data);
  }

  if (mutating) invalidateForPath(path);
  return (body as DataEnvelope<T>).data;
}

// Multipart upload (e.g. CSV import). Posts FormData WITHOUT a Content-Type header so the browser
// sets the multipart boundary itself; unwraps the {data}/{error} envelope like apiFetch.
export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const headers = new Headers();
  headers.set("Accept-Language", activeLanguage());

  const res = await authedFetch(path, { method: "POST", body: form }, headers);

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
      typeof env?.error?.message === "string" ? env.error.message : `Request failed (${res.status})`;
    throw new ApiError(msg, res.status, env?.error?.code, env?.error?.data);
  }

  invalidateForPath(path);
  return (body as DataEnvelope<T>).data;
}

// Authenticated file download (CSV/XLSX report exports). Streams the response to a blob and
// triggers a browser download, taking the filename from the Content-Disposition header.
export async function downloadExport(path: string, fallbackName = "export"): Promise<void> {
  const headers = new Headers();

  const res = await authedFetch(path, {}, headers);
  if (!res.ok) {
    if (res.status === 401) setToken(null);
    throw new ApiError(`Export failed (${res.status})`, res.status);
  }

  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const name = match ? match[1] : fallbackName;

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
