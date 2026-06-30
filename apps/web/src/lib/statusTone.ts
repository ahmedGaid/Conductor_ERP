import type { BadgeTone } from "../components/Badge";

// Domain status → Badge tone. These reproduce, 1:1, the status-modifier CSS each module
// used to carry (.sales-badge--*, .pur-badge--*, .crm-badge--*). Any status without an
// explicit entry falls back to `pending` — exactly the base recipe's old default.

const SALES_TONES: Record<string, BadgeTone> = {
  confirmed: "running",
  delivered: "waiting",
  invoiced: "accent",
  paid: "completed",
  cancelled: "failed",
};

const PURCHASING_TONES: Record<string, BadgeTone> = {
  confirmed: "running",
  received: "waiting",
  billed: "accent",
  paid: "completed",
  cancelled: "failed",
};

const CRM_TONES: Record<string, BadgeTone> = {
  new: "pending",
  open: "pending",
  qualifying: "pending",
  contacted: "running",
  in_progress: "running",
  proposal: "running",
  active: "running",
  qualified: "waiting",
  negotiation: "waiting",
  converted: "completed",
  won: "completed",
  resolved: "completed",
  unqualified: "failed",
  lost: "failed",
  cancelled: "failed",
  closed: "neutral",
  draft: "neutral",
  completed: "neutral",
};

const CRM_PRIORITY_TONES: Record<string, BadgeTone> = {
  low: "neutral",
  medium: "running",
  high: "waiting",
  urgent: "failed",
};

export const salesTone = (status: string): BadgeTone => SALES_TONES[status] ?? "pending";
export const purchasingTone = (status: string): BadgeTone => PURCHASING_TONES[status] ?? "pending";
export const crmTone = (status: string): BadgeTone => CRM_TONES[status] ?? "pending";
export const crmPriorityTone = (priority: string): BadgeTone => CRM_PRIORITY_TONES[priority] ?? "neutral";
