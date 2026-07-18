import { apiFetch } from "./client";

export type ConfidenceSignalKey = "books" | "vat" | "backups" | "stock" | "assistant";
export type ConfidenceStatus = "ok" | "warn";

export interface ConfidenceSignal {
  key: ConfidenceSignalKey;
  status: ConfidenceStatus;
}

export function getConfidence(): Promise<{ signals: ConfidenceSignal[] }> {
  return apiFetch<{ signals: ConfidenceSignal[] }>("/dashboard/confidence/");
}
