// Typed client for the WorkSession draft API (/api/worksessions/*). Drafts are private to the user.
import { apiFetch, getToken } from "./client";

export type DraftStatus = "active" | "completed" | "discarded" | "superseded";

export interface WorkSessionDraft {
  id: string;
  workflow_key: string;
  entity_type: string;
  related_entity_id: string;
  status: DraftStatus;
  payload: unknown;
  schema_version: number;
  client_version: number;
  last_active_at: string;
}

export interface DraftSaveBody {
  workflow_key: string;
  payload: unknown;
  entity_type?: string;
  related_entity_id?: string;
  schema_version: number;
  client_version: number;
  expected_version?: number | null;
}

export function getActiveDraft(
  workflowKey: string,
  relatedEntityId = "",
): Promise<WorkSessionDraft | null> {
  const params = new URLSearchParams({ workflow_key: workflowKey });
  if (relatedEntityId) params.set("related_entity_id", relatedEntityId);
  return apiFetch<WorkSessionDraft | null>(`/worksessions/active?${params.toString()}`);
}

export function listDrafts(): Promise<WorkSessionDraft[]> {
  return apiFetch<WorkSessionDraft[]>("/worksessions/");
}

export function saveDraft(
  body: DraftSaveBody,
): Promise<{ session: WorkSessionDraft; conflict: boolean }> {
  return apiFetch("/worksessions/", { method: "POST", body: JSON.stringify(body) });
}

export function discardDraft(id: string): Promise<void> {
  return apiFetch(`/worksessions/${id}/discard`, { method: "POST", body: "{}" });
}

export function completeDraft(id: string, relatedEntityId = ""): Promise<WorkSessionDraft> {
  return apiFetch(`/worksessions/${id}/complete`, {
    method: "POST",
    body: JSON.stringify({ related_entity_id: relatedEntityId }),
  });
}

/**
 * Best-effort flush used on page hide/unload. `fetch(keepalive:true)` outlives the page AND carries
 * the in-memory JWT `Authorization` header (which `navigator.sendBeacon` cannot set, so a beacon
 * would post unauthenticated). Body is far under keepalive's 64 KB cap. Response is ignored.
 */
export function flushDraft(body: DraftSaveBody): void {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    void fetch("/api/worksessions/", {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      keepalive: true,
    });
  } catch {
    /* best-effort on unload — nothing else we can do */
  }
}
