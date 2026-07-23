// Shapes mirrored from the Django workflow API (erp/workflow/serializers.py).

export type NodeType =
  | "start"
  | "api_call"
  | "approval"
  | "assistant_action"
  | "condition"
  | "script"
  | "end";

/** One entry of the assistant action catalog an `assistant_action` node may be pointed at. */
export interface AssistantActionOption {
  name: string;
  description: string;
  kind: string;
  risk: string;
  args: string[];
}

export type InstanceStatus =
  | "pending"
  | "running"
  | "waiting"
  | "failed"
  | "completed";

export interface GraphNode {
  key: string;
  type: NodeType;
  config: Record<string, unknown>;
  position: { x?: number; y?: number };
}

export interface GraphEdge {
  source: string;
  target: string;
  condition: unknown | null;
  ordering: number;
}

export interface WorkflowGraph {
  id: string;
  name: string;
  version: number;
  status: string;
  created_at: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

/** One field a template asks the user to fill in before it's expanded into a workflow graph. */
export interface WorkflowTemplateField {
  key: string;
  type: "money" | "role" | "person" | "number";
  label: { ar: string; en: string };
}

/** One entry of the fixed non-technical workflow template catalog (erp/workflow/templates.py). */
export interface WorkflowTemplate {
  id: string;
  name: { ar: string; en: string };
  fields: WorkflowTemplateField[];
}

export interface WorkflowListItem {
  id: string;
  name: string;
  version: number;
  status: string;
  created_at: string;
  node_count: number;
  instance_count: number;
}

export interface ExecutionLog {
  level: "debug" | "info" | "warn" | "error";
  /** Stable event code (e.g. "advanced", "node_waiting") — translate via `instance.log.<message>`. */
  message: string;
  /** Interpolation values for the translated message (node keys, error text) — never prose. */
  data: Record<string, unknown> | null;
  correlation_id: string;
  created_at: string;
}

export interface NodeRun {
  node_key: string;
  node_type: NodeType;
  status: InstanceStatus;
  attempt: number;
  input: unknown | null;
  output: unknown | null;
  error: string;
  started_at: string | null;
  finished_at: string | null;
  logs: ExecutionLog[];
}

export interface InstanceSummary {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: InstanceStatus;
  current_node: string | null;
  error: string;
  created_at: string;
  updated_at: string;
}

export interface ApprovalRequestInfo {
  id: string;
  approver_role: string;
  approver_user: string | null;
  title: string;
  message: string;
  status: "pending" | "approved" | "rejected";
  decided_by: string | null;
  comment: string;
  decided_at: string | null;
  created_at: string;
}

export interface InstanceDetail extends InstanceSummary {
  context: Record<string, unknown>;
  node_runs: NodeRun[];
  approval: ApprovalRequestInfo | null;
}

export interface DashboardMetrics {
  workflows_total: number;
  workflows_active: number;
  instances_total: number;
  instances_by_status: Record<InstanceStatus, number>;
  instances_waiting: number;
  instances_failed: number;
}
