// Minimal fetch wrapper for the Django API.
// - Prefixes /api, attaches the JWT bearer, and unwraps the {data} / {error} envelope.
// - On a successful write (non-GET), evicts the cached lists that write affects, so created/
//   changed records show up immediately the next time their list is viewed.
// - Vite proxies /api -> http://localhost:8000 in dev (see vite.config.ts).

import { invalidateForPath } from "../lib/cache";

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
    throw new ApiError(msg, res.status, env?.error?.code);
  }

  if (mutating) invalidateForPath(path);
  return (body as DataEnvelope<T>).data;
}

// Authenticated file download (CSV/XLSX report exports). Streams the response to a blob and
// triggers a browser download, taking the filename from the Content-Disposition header.
export async function downloadExport(path: string, fallbackName = "export"): Promise<void> {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`/api${path}`, { headers });
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
