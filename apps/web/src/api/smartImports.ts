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
  row_count: number;
  processed_count: number;
  error_count: number;
  stats: ImportStats;
  profile_id: string | null;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface ImportStats {
  rows?: number;
  existing?: Record<string, number>;
  new_refs?: Record<string, string[]>;
  issues_by_code?: Record<string, number>;
  duplicates_in_file?: number;
  [key: string]: unknown;
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
