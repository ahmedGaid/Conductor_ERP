// Typed wrappers around the workflow API endpoints.
import { apiFetch } from "./client";
import type {
  AssistantActionOption,
  DashboardMetrics,
  GraphEdge,
  GraphNode,
  InstanceDetail,
  InstanceStatus,
  InstanceSummary,
  WorkflowGraph,
  WorkflowListItem,
} from "./types";

export interface GraphPayload {
  name: string;
  status?: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export function getMetrics(): Promise<DashboardMetrics> {
  return apiFetch<DashboardMetrics>("/workflow/dashboard/metrics");
}

/** The catalog an assistant-action step may be pointed at (draft actions only, by design). */
export function listAssistantActions(): Promise<AssistantActionOption[]> {
  return apiFetch<AssistantActionOption[]>("/workflow/assistant-actions");
}

export function listWorkflows(): Promise<WorkflowListItem[]> {
  return apiFetch<WorkflowListItem[]>("/workflow/workflows");
}

export function getWorkflow(id: string): Promise<WorkflowGraph> {
  return apiFetch<WorkflowGraph>(`/workflow/workflows/${id}`);
}

export function createWorkflow(payload: GraphPayload): Promise<WorkflowGraph> {
  return apiFetch<WorkflowGraph>("/workflow/workflows", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateWorkflow(id: string, payload: GraphPayload): Promise<WorkflowGraph> {
  return apiFetch<WorkflowGraph>(`/workflow/workflows/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function startInstance(
  id: string,
  payload: Record<string, unknown> = {},
): Promise<InstanceDetail> {
  return apiFetch<InstanceDetail>(`/workflow/workflows/${id}/start`, {
    method: "POST",
    body: JSON.stringify({ payload }),
  });
}

export function listInstances(params: {
  workflow?: string;
  status?: InstanceStatus;
} = {}): Promise<InstanceSummary[]> {
  const q = new URLSearchParams();
  if (params.workflow) q.set("workflow", params.workflow);
  if (params.status) q.set("status", params.status);
  const qs = q.toString();
  return apiFetch<InstanceSummary[]>(`/workflow/instances${qs ? `?${qs}` : ""}`);
}

export function getInstance(id: string): Promise<InstanceDetail> {
  return apiFetch<InstanceDetail>(`/workflow/instances/${id}`);
}

export function decideInstance(
  id: string,
  decision: "approve" | "reject",
  comment = "",
): Promise<InstanceDetail> {
  return apiFetch<InstanceDetail>(`/workflow/instances/${id}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, comment }),
  });
}
