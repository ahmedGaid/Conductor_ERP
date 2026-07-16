import { apiFetch } from "./client";

export interface Branch {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export function listBranches(): Promise<Branch[]> {
  return apiFetch<Branch[]>("/core/branches");
}

export function createBranch(payload: { code: string; name: string }): Promise<Branch> {
  return apiFetch<Branch>("/core/branches", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateBranch(code: string, changes: Partial<Branch>): Promise<Branch> {
  return apiFetch<Branch>(`/core/branches/${encodeURIComponent(code)}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}
