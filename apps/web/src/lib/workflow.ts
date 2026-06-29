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

// --- Stage history -----------------------------------------------------------------------------
// The backend stores a point-in-time snapshot of the order at every transition (audit trail). A
// stage's history entry lets the tracker show who reached it, when, and the order as it was then.

export interface SnapshotLine {
  line_no: number;
  item_sku: string;
  description: string;
  quantity: string;
  /** Sales orders carry delivered_qty; purchase orders carry received_qty. */
  delivered_qty?: string;
  received_qty?: string;
  returned_qty: string;
  unit_price_minor?: number;
  unit_cost_minor?: number;
  discount_minor?: number;
  line_total_minor: number;
}

export interface OrderSnapshot {
  number: string;
  status: string;
  customer_code?: string;
  customer_name?: string;
  supplier_code?: string;
  supplier_name?: string;
  warehouse_code: string;
  currency: string;
  order_date: string;
  subtotal_minor: number;
  tax_minor: number;
  invoiced_minor?: number;
  billed_minor?: number;
  paid_minor: number;
  returned_minor: number;
  outstanding_minor: number;
  invoice_number?: string;
  credit_note_number?: string;
  bill_number?: string;
  debit_note_number?: string;
  lines: SnapshotLine[];
}

export interface StageHistoryEntry {
  action: string;
  /** Workflow stage key this entry belongs to (or null when the action has no forward stage). */
  stage: string | null;
  actor_name: string | null;
  /** ISO timestamp. */
  at: string;
  snapshot: OrderSnapshot | null;
}

/** Latest history entry per stage key, so a stage shows the order as it was when last reached. */
export function historyByStage(history: StageHistoryEntry[]): Record<string, StageHistoryEntry> {
  const map: Record<string, StageHistoryEntry> = {};
  for (const entry of history) {
    if (entry.stage) map[entry.stage] = entry; // ordered oldest→newest, so the last wins
  }
  return map;
}
