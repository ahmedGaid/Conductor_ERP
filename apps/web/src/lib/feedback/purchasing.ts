/*
 * Purchasing action feedback — the buy-side mirror of `feedback/sales.ts`: turns a completed
 * purchase transaction into a rich ActionReceipt (the result, what it means, the recommended next
 * step, quick actions, related records, the numbers, and any produced bill / debit note).
 *
 * Unlike sales there is no deterministic insight engine: receiving *adds* stock (so there's no
 * shortage to warn about) and suppliers carry no credit limit — so purchasing receipts stay to the
 * facts. Errors still get a rich receipt with a retry, for one consistent after-action surface.
 *
 * All copy is i18n (feedback.purchasing.*); resolvers stay free of page/DOM concerns — the page
 * passes its own runners (optimistic action, navigate, duplicate, print) as `deps`.
 */
import type { TFunction } from "i18next";

import type { ActionFeedbackApi, ActionReceipt, ReceiptAction, ReceiptLink } from "../../app/ActionFeedbackContext";
import type { PurchaseOrder, PurchaseRequest } from "../../api/purchasing";
import { formatMinor } from "../money";

/** The lifecycle events a purchase-order receipt can report. */
export type POEvent =
  | "created"
  | "approved"
  | "confirmed"
  | "received"
  | "billed"
  | "paid"
  | "returned"
  | "cancelled"
  | "converted";

/** The recommended next step's action key — the page maps this back to its optimistic runner. */
export type POActionKey = "approve" | "confirm" | "receive" | "bill" | "pay" | "return";

export interface POReceiptDeps {
  /** Perform the recommended next step (page-owned optimistic action). */
  run?: (key: POActionKey) => void;
  navigate: (to: string) => void;
  duplicate?: () => void;
  print?: () => void;
}

// The single most-likely next step for a PO, mirroring PurchaseOrderDetailPage's primary action so
// the receipt and the page always agree. Returns null at a terminal state.
function nextStep(o: PurchaseOrder): { key: POActionKey; icon: string } | null {
  if (o.status === "draft" && o.requires_approval && !o.approved) return { key: "approve", icon: "check" };
  if (o.status === "draft") return { key: "confirm", icon: "checkCircle" };
  if (o.status === "confirmed" || o.status === "partially_received") return { key: "receive", icon: "inventory" };
  if (o.status === "received") return { key: "bill", icon: "accounting" };
  if (o.status === "billed") return { key: "pay", icon: "accounting" };
  return null;
}

function orderFacts(t: TFunction, o: PurchaseOrder) {
  return [
    { label: t("purchasing.orders.supplier"), value: o.supplier_name || o.supplier_code },
    { label: t("feedback.fact.amount"), value: formatMinor(o.subtotal_minor + o.tax_minor, o.currency) },
    { label: t("feedback.fact.items"), value: String(o.lines.length) },
    { label: t("feedback.fact.status"), value: t(`purchasing.status.${o.status}`) },
  ];
}

// Records this action produced — the numbers worth a one-click open (the GL entry of the bill /
// debit note). Shown in both simple and rich modes.
function orderDocuments(t: TFunction, o: PurchaseOrder): ReceiptLink[] {
  const docs: ReceiptLink[] = [];
  if (o.bill_number)
    docs.push({ label: t("feedback.doc.bill", { no: o.bill_number }), to: `/go/journal/${encodeURIComponent(o.bill_number)}` });
  if (o.debit_note_number)
    docs.push({ label: t("feedback.doc.debitNote", { no: o.debit_note_number }), to: `/go/journal/${encodeURIComponent(o.debit_note_number)}` });
  return docs;
}

// Navigation links (rich mode only).
function orderRelated(t: TFunction, o: PurchaseOrder): ReceiptLink[] {
  return [
    { label: t("feedback.related.supplier"), to: `/purchasing/suppliers/${encodeURIComponent(o.supplier_code)}` },
    { label: t("feedback.related.purchaseOrders"), to: "/purchasing" },
  ];
}

/** Build (but don't show) a purchase-order receipt for a given event. */
export function orderReceipt(
  t: TFunction,
  o: PurchaseOrder,
  event: POEvent,
  deps: POReceiptDeps,
): ActionReceipt {
  const next = nextStep(o);
  const nextAction: ReceiptAction | undefined =
    next && deps.run
      ? { label: t(`feedback.purchasing.step.${next.key}`), icon: next.icon, run: () => deps.run!(next.key) }
      : undefined;

  const quick: ReceiptAction[] = [];
  if (deps.duplicate) quick.push({ label: t("document.duplicate"), icon: "duplicate", run: deps.duplicate });
  if (deps.print) quick.push({ label: t("document.print"), icon: "print", run: deps.print });
  quick.push({ label: t("feedback.action.newPO"), icon: "purchasing", run: () => deps.navigate("/purchasing/orders/new") });

  return {
    variant: "success",
    title: t(`feedback.purchasing.po.${event}.title`, { number: o.number }),
    context: t(`feedback.purchasing.po.${event}.context`, { amount: formatMinor(o.outstanding_minor, o.currency) }),
    next: nextAction,
    documents: orderDocuments(t, o),
    quickActions: quick,
    related: orderRelated(t, o),
    facts: orderFacts(t, o),
  };
}

/** Show a purchase-order receipt for the given lifecycle event. */
export function showPurchaseOrderReceipt(
  fb: ActionFeedbackApi,
  t: TFunction,
  o: PurchaseOrder,
  event: POEvent,
  deps: POReceiptDeps,
): void {
  fb.show(orderReceipt(t, o, event, deps));
}

// The attempted event → the action key to retry once the blocker is cleared.
const RETRY_KEY: Partial<Record<POEvent, POActionKey>> = {
  approved: "approve",
  confirmed: "confirm",
  received: "receive",
  billed: "bill",
  paid: "pay",
  returned: "return",
};

/** Show a failed purchase-order action as a rich error receipt: what went wrong, and a retry. */
export function showPurchaseOrderError(
  fb: ActionFeedbackApi,
  t: TFunction,
  o: PurchaseOrder,
  event: POEvent,
  error: unknown,
  deps: { run?: (key: POActionKey) => void },
): void {
  const rawMessage = error instanceof Error ? error.message : String(error);
  const retryKey = RETRY_KEY[event];
  const next: ReceiptAction | undefined =
    retryKey && deps.run ? { label: t("feedback.purchasing.action.retry"), icon: "rotate", run: () => deps.run!(retryKey) } : undefined;

  fb.show({
    variant: "error",
    title: t(`feedback.purchasing.error.${event}.title`, { number: o.number }),
    context: t(`feedback.purchasing.error.${event}.reason`, { defaultValue: rawMessage }),
    next,
  });
}

// --- Purchase requests -----------------------------------------------------------------------

export type RequestEvent = "created" | "submitted" | "approved" | "rejected";

export interface RequestReceiptDeps {
  /** Perform the recommended next step (submit / approve / convert). */
  run?: () => void;
  navigate: (to: string) => void;
  duplicate?: () => void;
}

function nextRequestStep(r: PurchaseRequest): { key: "submit" | "approve" | "convert" } | null {
  if (r.status === "draft") return { key: "submit" };
  if (r.status === "submitted") return { key: "approve" };
  if (r.status === "approved") return { key: "convert" };
  return null;
}

export function showRequestReceipt(
  fb: ActionFeedbackApi,
  t: TFunction,
  r: PurchaseRequest,
  event: RequestEvent,
  deps: RequestReceiptDeps,
): void {
  const next = nextRequestStep(r);
  const nextAction: ReceiptAction | undefined =
    next && deps.run ? { label: t(`feedback.purchasing.reqStep.${next.key}`), icon: "checkCircle", run: deps.run } : undefined;

  const quick: ReceiptAction[] = [];
  if (deps.duplicate) quick.push({ label: t("document.duplicate"), icon: "duplicate", run: deps.duplicate });
  quick.push({ label: t("feedback.action.newRequest"), icon: "purchasing", run: () => deps.navigate("/purchasing/requests/new") });

  const documents: ReceiptLink[] = r.converted_order_number
    ? [{ label: t("feedback.doc.purchaseOrder", { no: r.converted_order_number }), to: `/go/purchase_order/${encodeURIComponent(r.converted_order_number)}` }]
    : [];

  fb.show({
    variant: event === "rejected" ? "info" : "success",
    title: t(`feedback.purchasing.request.${event}.title`, { number: r.number }),
    context: t(`feedback.purchasing.request.${event}.context`),
    next: nextAction,
    documents,
    quickActions: quick,
    related: [
      { label: t("feedback.related.supplier"), to: `/purchasing/suppliers/${encodeURIComponent(r.supplier_code)}` },
      { label: t("feedback.related.requests"), to: "/purchasing/requests" },
    ],
    facts: [
      { label: t("purchasing.orders.supplier"), value: r.supplier_name || r.supplier_code },
      { label: t("feedback.fact.amount"), value: formatMinor(r.subtotal_minor, r.currency) },
      { label: t("feedback.fact.items"), value: String(r.lines.length) },
      { label: t("feedback.fact.status"), value: t(`purchasing.requestStatus.${r.status}`) },
    ],
  });
}

// --- Suppliers -------------------------------------------------------------------------------

export function showSupplierReceipt(
  fb: ActionFeedbackApi,
  t: TFunction,
  supplier: { code: string; name: string },
  deps: { navigate: (to: string) => void },
): void {
  fb.show({
    variant: "success",
    title: t("feedback.purchasing.supplier.created.title", { name: supplier.name }),
    context: t("feedback.purchasing.supplier.created.context"),
    next: {
      label: t("feedback.action.newPOFor"),
      icon: "purchasing",
      run: () => deps.navigate("/purchasing/orders/new"),
    },
    related: [
      { label: t("feedback.related.supplier"), to: `/purchasing/suppliers/${encodeURIComponent(supplier.code)}` },
      { label: t("feedback.related.suppliers"), to: "/purchasing/suppliers" },
    ],
    facts: [{ label: t("purchasing.orders.supplier"), value: supplier.name || supplier.code }],
  });
}
