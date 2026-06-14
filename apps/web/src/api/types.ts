// Shapes mirrored from the Django workflow API (erp/workflow/serializers.py).

export type NodeType = "start" | "api_call" | "approval" | "condition" | "script" | "end";

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
  message: string;
  data: unknown | null;
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

export interface InstanceDetail extends InstanceSummary {
  context: Record<string, unknown>;
  node_runs: NodeRun[];
}

export interface DashboardMetrics {
  workflows_total: number;
  workflows_active: number;
  instances_total: number;
  instances_by_status: Record<InstanceStatus, number>;
  instances_waiting: number;
  instances_failed: number;
}
