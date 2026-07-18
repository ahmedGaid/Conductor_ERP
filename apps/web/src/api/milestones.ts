import { apiFetch } from "./client";

export type MilestoneKind = "invoice_count" | "first_profitable_month";

export interface Milestone {
  key: string;
  kind: MilestoneKind;
  value: number | null;
}

export function getPendingMilestone(): Promise<{ milestone: Milestone | null }> {
  return apiFetch<{ milestone: Milestone | null }>("/dashboard/milestones/");
}

export function dismissMilestone(key: string): Promise<{ key: string; dismissed: boolean }> {
  return apiFetch<{ key: string; dismissed: boolean }>(`/dashboard/milestones/${key}/dismiss/`, {
    method: "POST",
    body: "{}",
  });
}
