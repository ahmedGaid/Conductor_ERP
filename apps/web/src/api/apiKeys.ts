import { apiFetch } from "./client";

// API keys settings API (/api/identity/api-keys, /api/identity/api-docs). Admin-only.

export interface ApiKeyRow {
  id: number;
  name: string;
  prefix: string;
  role: string;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
  is_active: boolean;
}

export interface ApiKeyWithSecret extends ApiKeyRow {
  secret: string;
}

export interface ApiRoute {
  path: string;
  view: string;
  methods: string[];
}

export function listApiKeys(): Promise<ApiKeyRow[]> {
  return apiFetch<ApiKeyRow[]>("/identity/api-keys");
}

export function createApiKey(payload: {
  name: string;
  role: string;
  expires_at?: string | null;
}): Promise<ApiKeyWithSecret> {
  return apiFetch<ApiKeyWithSecret>("/identity/api-keys", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function revokeApiKey(id: number): Promise<ApiKeyRow> {
  return apiFetch<ApiKeyRow>(`/identity/api-keys/${id}/revoke`, { method: "POST" });
}

export function listApiRoutes(): Promise<{ routes: ApiRoute[] }> {
  return apiFetch<{ routes: ApiRoute[] }>("/identity/api-docs");
}
