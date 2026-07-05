// Typed wrapper for the audit API (/api/audit/*) — the per-record activity timeline.
import { apiFetch } from "./client";

export interface RecordChange {
  field: string;
  old: unknown;
  new: unknown;
}

export interface RecordHistoryEntry {
  action: string;
  actor_name: string | null;
  at: string;
  changes: RecordChange[];
}

export function getRecordHistory(entityType: string, entityId: string): Promise<RecordHistoryEntry[]> {
  const qs = `entity_type=${encodeURIComponent(entityType)}&entity_id=${encodeURIComponent(entityId)}`;
  return apiFetch<RecordHistoryEntry[]>(`/audit/history?${qs}`);
}
