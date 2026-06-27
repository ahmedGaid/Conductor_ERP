// Generic CSV-import client, shared by every importable list (customers first; suppliers/items next).
// The server runs the same engine for preview and commit, so a preview is exactly what commit does.
import { apiUpload, downloadExport } from "./client";

export type ImportOutcome = "created" | "updated" | "skipped" | "failed";

export interface ImportRowError {
  field: string;
  message: string;
}

export interface ImportRow {
  row: number;
  outcome: ImportOutcome;
  key: string;
  errors: ImportRowError[];
}

export interface ImportSummary {
  total: number;
  created: number;
  updated: number;
  skipped: number;
  failed: number;
}

export interface ImportResult {
  headers: string[];
  mapping: Record<string, string>;
  summary: ImportSummary;
  committed: boolean;
  rows: ImportRow[];
}

export interface ImportOptions {
  mapping?: Record<string, string>;
  mode?: "create" | "upsert";
  commit?: boolean;
}

/** One canonical column the import targets (label is already translated by the caller). */
export interface ImportFieldInfo {
  name: string;
  label: string;
  required?: boolean;
}

/** Preview (commit=false) or apply (commit=true) an import for a list at `basePath`. */
export function runImport(basePath: string, file: File, opts: ImportOptions = {}): Promise<ImportResult> {
  const form = new FormData();
  form.append("file", file);
  if (opts.mapping) form.append("mapping", JSON.stringify(opts.mapping));
  if (opts.mode) form.append("mode", opts.mode);
  form.append("commit", opts.commit ? "true" : "false");
  return apiUpload<ImportResult>(`${basePath}/import`, form);
}

/** Download the per-list CSV template (canonical headers + one example row). */
export function downloadImportTemplate(basePath: string, fallbackName: string): Promise<void> {
  return downloadExport(`${basePath}/import/template`, fallbackName);
}
