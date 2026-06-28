// Lifecycle definitions for the always-visible workflow tracker (WorkflowTracker.tsx).
// Maps a document's backend status onto an ordered set of human stages so the user always
// sees the whole journey and where they are in it. Display-layer only — the real status
// enum/lifecycle is unchanged.

export type StepState = "done" | "current" | "todo";

export interface WfStep {
  key: string;
  state: StepState;
  /** Branch step (return / cancellation) — shown as an exception, not a forward stage. */
  exception?: boolean;
}

export type WorkflowKind = "sales" | "purchasing";

const SALES_STAGES = ["create", "confirm", "deliver", "invoice", "payment"];
const PURCHASING_STAGES = ["create", "confirm", "receive", "bill", "payment"];

// How many forward stages are complete at each status.
const SALES_DONE: Record<string, number> = {
  new: 0,
  draft: 1,
  confirmed: 2,
  partially_delivered: 2,
  delivered: 3,
  invoiced: 4,
  paid: 5,
  returned: 5,
  cancelled: 1,
};
const PURCHASING_DONE: Record<string, number> = {
  new: 0,
  draft: 1,
  confirmed: 2,
  partially_received: 2,
  received: 3,
  billed: 4,
  paid: 5,
  returned: 5,
  cancelled: 1,
};

function build(stages: string[], doneMap: Record<string, number>, status: string): WfStep[] {
  const done = doneMap[status] ?? 1;
  const steps: WfStep[] = stages.map((key, i) => ({
    key,
    state: i < done ? "done" : i === done ? "current" : "todo",
  }));
  if (status === "returned") steps.push({ key: "returned", state: "current", exception: true });
  if (status === "cancelled") steps.push({ key: "cancelled", state: "current", exception: true });
  return steps;
}

export function workflowFor(kind: WorkflowKind, status: string): WfStep[] {
  return kind === "sales"
    ? build(SALES_STAGES, SALES_DONE, status)
    : build(PURCHASING_STAGES, PURCHASING_DONE, status);
}
