// Typed wrappers around the workflow template API endpoints (non-technical builder front door).
import { apiFetch } from "./client";
import type { WorkflowGraph, WorkflowTemplate } from "./types";

export type { WorkflowTemplate };

export function listTemplates(): Promise<WorkflowTemplate[]> {
  return apiFetch<WorkflowTemplate[]>("/workflow/workflows/templates");
}

export function createFromTemplate(
  templateId: string,
  name: string,
  params: Record<string, unknown>,
): Promise<WorkflowGraph> {
  return apiFetch<WorkflowGraph>(`/workflow/workflows/templates/${templateId}`, {
    method: "POST",
    body: JSON.stringify({ name, params }),
  });
}
