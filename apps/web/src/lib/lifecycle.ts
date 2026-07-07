// Per-document-type lifecycle stage maps — the single source that feeds the StatusRing arc.
// Built from the real status unions in api/*.ts (sales, purchasing, e-invoicing, accounting
// journals, CRM), NOT from memory. Each map is the ORDERED list of on-line stages a document
// walks from draft to its terminal-good end. A status that is NOT on the line (cancelled /
// rejected / lost / unqualified — a document that stopped, not one that progressed) has no
// fraction: it renders as a hollow ring beside its status word, never a fake "progress".
//
// Fraction convention (decision 5, FILE_00): draft is the FIRST step (never 0 — a fresh draft
// still shows a sliver of ring), the terminal-good stage is 1.0. So a stage at index i of n
// stages fills (i + 1) / n.

export type LifecycleDocType =
  | "salesOrder"
  | "purchaseOrder"
  | "quotation"
  | "purchaseRequest"
  | "einvoice"
  | "journal"
  | "lead"
  | "opportunity"
  | "ticket"
  | "campaign";

// Ordered on-line stages only. Off-line terminals (cancelled/rejected/lost/unqualified/returned)
// are deliberately absent → lifecycleFraction returns null for them (hollow ring).
const STAGES: Record<LifecycleDocType, readonly string[]> = {
  // OrderStatus — partially_delivered sits between confirmed and delivered.
  salesOrder: ["draft", "confirmed", "partially_delivered", "delivered", "invoiced", "paid"],
  // POStatus — mirror of the sales line on the buy side.
  purchaseOrder: ["draft", "confirmed", "partially_received", "received", "billed", "paid"],
  // QuotationStatus — draft → submitted → approved → converted (to an order).
  quotation: ["draft", "submitted", "approved", "converted"],
  // PRStatus — same shape as a quotation.
  purchaseRequest: ["draft", "submitted", "approved", "converted"],
  // ETAStatus — draft → submitted (to the ETA) → valid.
  einvoice: ["draft", "submitted", "valid"],
  // Journals are posted on creation; the only progression is draft → posted.
  journal: ["draft", "posted"],
  // LeadStatus — new → contacted → qualified → converted (to an opportunity).
  lead: ["new", "contacted", "qualified", "converted"],
  // OppStage — qualifying → proposal → negotiation → won.
  opportunity: ["qualifying", "proposal", "negotiation", "won"],
  // TicketStatus — open → in_progress → resolved → closed.
  ticket: ["open", "in_progress", "resolved", "closed"],
  // CampaignStatus — draft → active → completed.
  campaign: ["draft", "active", "completed"],
};

/**
 * How far along its lifecycle a document sits, as a fraction in (0, 1].
 * Returns `null` when the status is not on the line (cancelled / rejected / lost / unqualified,
 * or an unknown status) — the caller renders a hollow ring beside the status word, no fill.
 */
export function lifecycleFraction(docType: LifecycleDocType, status: string): number | null {
  const stages = STAGES[docType];
  const i = stages.indexOf(status);
  if (i < 0) return null;
  return (i + 1) / stages.length;
}
