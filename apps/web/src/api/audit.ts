// Typed wrapper for the audit API (/api/audit/*) — the per-record activity timeline.
import { apiFetch } from "./client";

export interface RecordChange {
  field: string;
  old: unknown;
  new: unknown;
}

export interface TimelineEntry {
  event: string;
  actor: string | null;
  at: string;
  params: Record<string, unknown>;
  changes: RecordChange[];
  /** Set when the entry was written by the AI assistant or an import batch, not a direct user edit. */
  source: "ai" | "import" | null;
}

export interface TimelinePage {
  items: TimelineEntry[];
  page: number;
  page_size: number;
  total: number;
}

export function getRecordTimeline(
  entityType: string,
  entityId: string,
  page = 1,
  pageSize = 20,
): Promise<TimelinePage> {
  const qs = `entity=${encodeURIComponent(entityType)}&id=${encodeURIComponent(entityId)}&page=${page}&page_size=${pageSize}`;
  return apiFetch<TimelinePage>(`/audit/timeline/?${qs}`);
}
