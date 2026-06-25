import { apiFetch } from "./client";

// Admin user-management API (Increment 3). Gated server-side by administration.user.* permissions.

export interface UserRow {
  id: number;
  username: string;
  email: string;
  display_name: string;
  role: string | null;
  roles: string[];
  branch: string | null;
  department: string | null;
  status: "active" | "invited" | "suspended" | "archived";
  last_login: string | null;
}

export interface PermissionGrant {
  code: string;
  scope: string;
}

export interface SessionRow {
  action: string;
  at: string;
  result: string;
  correlation_id: string;
}

export interface AuditRow {
  module: string;
  action: string;
  entity_type: string;
  entity_id: string;
  at: string;
  result: string;
}

export interface ActiveSession {
  id: number;
  created_at: string | null;
  expires_at: string | null;
}

export interface UserDetail extends UserRow {
  job_title: string;
  phone: string;
  team: string | null;
  is_2fa_enabled: boolean;
  modules: string[];
  permissions: PermissionGrant[];
  sessions: SessionRow[];
  active_sessions: ActiveSession[];
  audit: AuditRow[];
  temp_password?: string;
}

export interface OrgUnits {
  roles: string[];
  branches: { code: string; name: string }[];
  departments: { code: string; name: string }[];
  teams: { code: string; name: string }[];
}

export interface UserFilters {
  search?: string;
  role?: string;
  status?: string;
  branch?: string;
  department?: string;
}

export function listUsers(filters: UserFilters = {}): Promise<UserRow[]> {
  const q = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v) as [string, string][],
  ).toString();
  return apiFetch<UserRow[]>(`/identity/users${q ? `?${q}` : ""}`);
}

export function getUser(id: number): Promise<UserDetail> {
  return apiFetch<UserDetail>(`/identity/users/${id}`);
}

export function createUser(body: {
  username: string;
  email: string;
  role?: string;
  branch?: string;
  department?: string;
  team?: string;
}): Promise<UserDetail> {
  return apiFetch<UserDetail>("/identity/users", { method: "POST", body: JSON.stringify(body) });
}

export function updateUser(
  id: number,
  changes: Partial<{
    role: string;
    branch: string | null;
    department: string | null;
    team: string | null;
    status: string;
    job_title: string;
    phone: string;
  }>,
): Promise<UserDetail> {
  return apiFetch<UserDetail>(`/identity/users/${id}`, { method: "PATCH", body: JSON.stringify(changes) });
}

export function resetUserPassword(id: number): Promise<{ temp_password: string }> {
  return apiFetch<{ temp_password: string }>(`/identity/users/${id}/reset-password`, { method: "POST" });
}

export function bulkUsers(
  action: "suspend" | "activate" | "archive" | "assign_role",
  ids: number[],
  role?: string,
): Promise<{ affected: number }> {
  return apiFetch<{ affected: number }>("/identity/users/bulk", {
    method: "POST",
    body: JSON.stringify({ action, ids, role }),
  });
}

export function getOrgUnits(): Promise<OrgUnits> {
  return apiFetch<OrgUnits>("/identity/users/org-units");
}

export function revokeAllSessions(id: number): Promise<{ revoked: number }> {
  return apiFetch<{ revoked: number }>(`/identity/users/${id}/revoke-sessions`, { method: "POST" });
}

export function revokeSession(id: number, tokenId: number): Promise<UserDetail> {
  return apiFetch<UserDetail>(`/identity/users/${id}/sessions/${tokenId}/revoke`, { method: "POST" });
}
