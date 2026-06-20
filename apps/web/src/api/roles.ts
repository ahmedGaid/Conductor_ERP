import { apiFetch } from "./client";

// Role editor API (Increment 4). Gated server-side by administration.role.* permissions.

export interface RoleRow {
  name: string;
  protected: boolean;
  members: number;
  permission_count: number;
  modules: string[];
}

export interface RoleDetail {
  name: string;
  protected: boolean;
  is_admin: boolean;
  members: number;
  permissions: Record<string, string>; // "<module>.<entity>.<action>" -> scope
  approval_limits: Record<string, number | null>; // document_type -> limit_minor | null (unlimited)
  modules: string[];
}

export interface RoleRegistry {
  modules: Record<string, string[]>; // module -> [entity, ...]
  actions: string[]; // [view, create, edit, delete, approve]
  scopes: { value: string; label: string }[];
  document_types: string[];
}

export function listRoles(): Promise<RoleRow[]> {
  return apiFetch<RoleRow[]>("/identity/roles");
}

export function getRoleRegistry(): Promise<RoleRegistry> {
  return apiFetch<RoleRegistry>("/identity/roles/registry");
}

export function getRole(name: string): Promise<RoleDetail> {
  return apiFetch<RoleDetail>(`/identity/roles/${encodeURIComponent(name)}`);
}

export function createRole(name: string, copyFrom?: string): Promise<RoleDetail> {
  return apiFetch<RoleDetail>("/identity/roles", {
    method: "POST",
    body: JSON.stringify({ name, copy_from: copyFrom || undefined }),
  });
}

export function deleteRole(name: string): Promise<{ deleted: string }> {
  return apiFetch<{ deleted: string }>(`/identity/roles/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}

export function setRolePermission(
  name: string,
  code: string,
  scope: string,
  granted: boolean,
): Promise<RoleDetail> {
  return apiFetch<RoleDetail>(`/identity/roles/${encodeURIComponent(name)}/permission`, {
    method: "POST",
    body: JSON.stringify({ code, scope, granted }),
  });
}

export type ApprovalLimitInput =
  | { limit_minor: number }
  | { unlimited: true }
  | { remove: true };

export function setApprovalLimit(
  name: string,
  documentType: string,
  value: ApprovalLimitInput,
): Promise<RoleDetail> {
  return apiFetch<RoleDetail>(`/identity/roles/${encodeURIComponent(name)}/approval-limit`, {
    method: "POST",
    body: JSON.stringify({ document_type: documentType, ...value }),
  });
}
