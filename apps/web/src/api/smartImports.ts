// Typed wrappers for the Smart Import Engine API (/api/imports — erp/imports app). Upload -> detect
// -> map -> analyze today (wizard sessions 12-14 fill preview/execute); see erp/imports/api/views.py
// for the server side. Distinct from api/imports.ts (the older per-list CSV import dialog, a
// different, still-active feature — kept separate to avoid a name/endpoint collision).
import { apiFetch, apiUpload } from "./client";

export type ImportFieldKind = "text" | "number" | "money" | "date" | "ref" | "enum";

export interface ImportFieldSpec {
  name: string;
  required: boolean;
  kind: ImportFieldKind;
  ref: string | null;
  enum: string[];
}

export interface ImportCandidate {
  entity: string;
  confidence: number; // 0-100
  label_key: string;
}

export interface ImportColumnSuggestion {
  field: string | null;
  confidence: number; // 0-100
  method: string;
}

export interface ImportProfileHit {
  id: string;
  name: string;
  entity: string;
  mapping: Record<string, string>; // field -> column
  options: Record<string, unknown>;
}

export interface ImportUploadResult {
  batch_id: string;
  file_info: {
    format: string;
    sheets: { name: string; row_count: number }[];
    encoding: string;
    delimiter: string | null;
  };
  headers: string[];
  samples: Record<string, string>[]; // sample rows, {header: value}
  candidates: ImportCandidate[];
  mapping_suggestion: Record<string, ImportColumnSuggestion>; // column -> suggestion
  profile_hits: ImportProfileHit[];
  entity_fields: Record<string, ImportFieldSpec[]>;
}

export interface ImportBatch {
  id: string;
  entity: string;
  status: string;
  strategy: string;
  mapping: Record<string, string>;
  fields: ImportFieldSpec[];
  // Grouped (document) entities only (FILE_15) — null/empty for every master adapter.
  group_by: string | null;
  header_fields: string[];
  file_name: string | null;
  row_count: number;
  processed_count: number;
  error_count: number;
  stats: ImportStats;
  profile_id: string | null;
  created_by: number;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImportStats {
  rows?: number;
  existing?: Record<string, number>;
  new_refs?: Record<string, string[]>;
  issues_by_code?: Record<string, number>;
  duplicates_in_file?: number;
  // written by the background runner (erp/imports/runner.py) while a batch is actually running
  stage?: "importing";
  rows_done?: number;
  rows_per_sec?: number;
  eta_seconds?: number | null;
  last_error?: string;
  rollback?: { reverted: number; skipped: number; cannot: RollbackCannotEntry[]; reverted_masters: string[] };
  // written by AccountOpeningAdapter.validate_group when a trial-balance import doesn't balance —
  // a human approves it via approveOpeningCorrection, never auto-applied.
  opening_correction?: {
    total_debit_minor: number;
    total_credit_minor: number;
    difference_minor: number;
    suspense_account: string;
    proposed_line: { account_ref: string; debit_minor: number; credit_minor: number };
    approved: boolean;
  };
  [key: string]: unknown;
}

export interface RollbackCannotEntry {
  row?: number;
  pk?: string;
  master?: { entity: string; value: string; pk: string };
  code?: "no_delete_path" | "no_update_restore" | "no_adapter" | "delete_failed";
  entity?: string;
  reason: string;
}

export interface ImportMappingResult {
  batch: ImportBatch;
  stats: ImportStats;
}

export function uploadImportFile(file: File): Promise<ImportUploadResult> {
  const form = new FormData();
  form.append("file", file);
  return apiUpload<ImportUploadResult>("/imports/upload", form);
}

export function postImportMapping(
  batchId: string,
  entity: string,
  mapping: Record<string, string>,
  profileId?: string,
): Promise<ImportMappingResult> {
  return apiFetch<ImportMappingResult>(`/imports/${batchId}/mapping`, {
    method: "POST",
    body: JSON.stringify({ entity, mapping, ...(profileId ? { profile_id: profileId } : {}) }),
  });
}

export function getImportBatch(batchId: string): Promise<ImportBatch> {
  return apiFetch<ImportBatch>(`/imports/${batchId}`);
}

// Mirrors every adapter's own `label_key = "imports.entity." + camelCase(entity)` convention
// (erp/imports/adapters/*.py) — used when only the raw entity slug is on hand (a resumed batch
// has no `label_key` of its own, unlike an upload response's candidates).
export function entityLabelKey(entity: string): string {
  const camel = entity.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
  return `imports.entity.${camel}`;
}

export function createImportProfile(
  name: string,
  entity: string,
  mapping: Record<string, string>,
): Promise<ImportProfileHit> {
  return apiFetch<ImportProfileHit>("/imports/profiles", {
    method: "POST",
    body: JSON.stringify({ name, entity, mapping }),
  });
}

// --- Review (session 13): rows, inline fix, autofix, creation plan, execute -------------------

export type ImportRowStatus = "pending" | "valid" | "error" | "duplicate" | "skipped" | "imported" | "reverted";

export interface ImportIssueCandidate {
  pk?: string; // an existing DB record
  row_number?: number; // another row in this same file
  label: string;
  score: number;
}

export interface ImportIssue {
  field: string;
  code: string;
  message: string;
  meta?: { entity?: string; value?: string; candidates?: ImportIssueCandidate[]; [key: string]: unknown };
}

export interface ImportRowDecision {
  duplicate?: "merge" | "create" | "ignore";
  target_pk?: string;
  edits?: Record<string, unknown>;
}

// Present only for a grouped (document) entity's rows (FILE_15) — null for every master adapter.
export interface ImportGroupMeta {
  group_id: string;
  is_first: boolean;
  key: string | null;
  header: Record<string, unknown>;
  computed_total_minor: number | null;
  line_count: number;
}

export interface ImportRowRow {
  row_number: number;
  raw: Record<string, unknown>;
  normalized: Record<string, unknown>;
  status: ImportRowStatus;
  issues: ImportIssue[];
  decision: ImportRowDecision;
  result_ref: Record<string, unknown>;
  group_meta: ImportGroupMeta | null;
}

export interface ImportRowsPage {
  rows: ImportRowRow[];
  page: number;
  page_size: number;
  total: number;
}

export function getImportRows(
  batchId: string,
  opts: { status?: string; page?: number; page_size?: number } = {},
): Promise<ImportRowsPage> {
  const params = new URLSearchParams();
  if (opts.status) params.set("status", opts.status);
  if (opts.page) params.set("page", String(opts.page));
  if (opts.page_size) params.set("page_size", String(opts.page_size));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<ImportRowsPage>(`/imports/${batchId}/rows${qs}`);
}

export function patchImportRow(
  batchId: string,
  rowNumber: number,
  patch: { decision?: ImportRowDecision; edits?: Record<string, unknown> },
): Promise<ImportRowRow> {
  return apiFetch<ImportRowRow>(`/imports/${batchId}/rows/${rowNumber}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export interface ImportFix {
  row_id: string;
  row: number;
  field: string;
  from: unknown;
  to: unknown;
  code: string;
}

export function getAutofixPreview(batchId: string): Promise<{ fixes: ImportFix[] }> {
  return apiFetch<{ fixes: ImportFix[] }>(`/imports/${batchId}/autofix`, { method: "POST" });
}

export function applyAutofix(
  batchId: string,
  fixes: ImportFix[],
): Promise<{ counts: Record<string, number> }> {
  return apiFetch<{ counts: Record<string, number> }>(`/imports/${batchId}/autofix/apply`, {
    method: "POST",
    body: JSON.stringify({ fixes }),
  });
}

// Approves the suspense-account balancing line AccountOpeningAdapter proposed for an out-of-balance
// trial balance, then re-validates so the batch's rows leave `error` — the only way to unblock an
// imbalanced account_opening import (FILE_17 acceptance: previously nothing could set this flag).
export function approveOpeningCorrection(
  batchId: string,
): Promise<{ batch: ImportBatch; counts: Record<string, number> }> {
  return apiFetch(`/imports/${batchId}/opening-correction/approve`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export interface ImportCreationPlanEntry {
  entity: string;
  value: string;
  action: "create" | "link" | "blocked_unsupported" | "blocked_permission";
  proposed?: Record<string, unknown>;
  link_pk?: string;
  confidence?: number;
  editable: boolean;
  outcome?: "created" | "linked";
}

// No `approved` key in the body → server BUILDS the plan (masters.build_creation_plan). Every
// distinct missing_ref becomes one proposed entry — never called automatically, so the review
// screen must trigger it once on mount.
export function buildCreationPlan(batchId: string): Promise<{ entries: ImportCreationPlanEntry[] }> {
  return apiFetch<{ entries: ImportCreationPlanEntry[] }>(`/imports/${batchId}/creation-plan`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

// `approved` (even empty) → server EXECUTES exactly those entries (masters.execute_creation_plan).
export function executeCreationPlan(
  batchId: string,
  approved: { entity: string; value: string }[],
): Promise<{ resolved: number; revalidated: Record<string, number> }> {
  return apiFetch(`/imports/${batchId}/creation-plan`, {
    method: "POST",
    body: JSON.stringify({ approved }),
  });
}

export interface ImportRowIssueEntry {
  row: number;
  issues: ImportIssue[];
}

export interface ImportReport {
  batch_id: string;
  entity: string;
  status: string;
  imported: number;
  created: number;
  updated: number;
  skipped: number;
  errors: number;
  error_rows: ImportRowIssueEntry[];
  warnings: ImportRowIssueEntry[];
  created_masters: { entity: string; value: string; pk: string }[];
  duration_seconds: number | null;
  row_outcomes: { row: number; status: ImportRowStatus; result_ref: Record<string, unknown> }[];
}

export function executeImport(
  batchId: string,
  opts: { strategy?: string; atomicity?: boolean; continue_after_errors?: boolean },
): Promise<{ queued: boolean; report?: ImportReport; batch?: ImportBatch }> {
  return apiFetch(`/imports/${batchId}/execute`, {
    method: "POST",
    body: JSON.stringify(opts),
  });
}

export function getImportReport(batchId: string): Promise<ImportReport> {
  return apiFetch<ImportReport>(`/imports/${batchId}/report`);
}

export function pauseImport(batchId: string): Promise<{ queued: boolean }> {
  return apiFetch(`/imports/${batchId}/pause`, { method: "POST" });
}

export function resumeImport(batchId: string): Promise<ImportBatch> {
  return apiFetch<ImportBatch>(`/imports/${batchId}/resume`, { method: "POST" });
}

export function cancelImport(batchId: string): Promise<{ queued: boolean }> {
  return apiFetch(`/imports/${batchId}/cancel`, { method: "POST" });
}

export interface ImportRollbackResult {
  reverted: number;
  skipped: number;
  cannot: RollbackCannotEntry[];
}

export function rollbackImport(batchId: string): Promise<ImportRollbackResult> {
  return apiFetch<ImportRollbackResult>(`/imports/${batchId}/rollback`, { method: "POST" });
}

export interface ImportBatchesPage {
  batches: ImportBatch[];
  page: number;
  page_size: number;
  total: number;
}

export function listImportBatches(opts: { entity?: string; page?: number; page_size?: number } = {}): Promise<ImportBatchesPage> {
  const params = new URLSearchParams();
  if (opts.entity) params.set("entity", opts.entity);
  if (opts.page) params.set("page", String(opts.page));
  if (opts.page_size) params.set("page_size", String(opts.page_size));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<ImportBatchesPage>(`/imports${qs}`);
}
