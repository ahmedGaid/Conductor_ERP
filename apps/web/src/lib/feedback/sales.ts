/*
 * Sales action feedback — turns a completed sales transaction into a rich ActionReceipt: the
 * result, what it means, the recommended next step, quick actions, related records, the numbers,
 * and deterministic insights (stock availability, credit headroom) drawn from existing APIs.
 *
 * Insights and warnings are computed frontend-side from data the app already serves; the base
 * receipt shows instantly and the async findings are merged in via `fb.update` when they land, so
 * feedback never waits on a lookup.
 *
 * All copy is i18n (feedback.sales.*); resolvers stay free of page/DOM concerns — the page passes
 * its own runners (optimistic action, navigate, duplicate, print) as `deps`.
 */
import type { TFunction } from "i18next";

import type { ActionFeedbackApi, ActionReceipt, ReceiptAction, ReceiptLink } from "../../app/ActionFeedbackContext";
import { listCustomers, listOrders, type Quotation, type SalesOrder } from "../../api/sales";
import { listItems, stockOnHand } from "../../api/inventory";
import { formatMinor } from "../money";

/** The lifecycle events an order receipt can report. */
export type OrderEvent =
  | "created"
  | "approved"
  | "confirmed"
  | "delivered"
  | "invoiced"
  | "paid"
  | "returned"
  | "cancelled"
  | "completed"
  | "converted";

/** The recommended next step's action key — the page maps this back to its optimistic runner. */
export type OrderActionKey = "approve" | "confirm" | "deliver" | "invoice" | "pay" | "return";

export interface OrderReceiptDeps {
  /** Perform the recommended next step (page-owned optimistic action). */
  run?: (key: OrderActionKey) => void;
  navigate: (to: string) => void;
  duplicate?: () => void;
  print?: () => void;
}

// The single most-likely next step for an order, mirroring OrderDetailPage's primary action so the
// receipt and the page always agree. Returns null at a terminal state.
function nextStep(o: SalesOrder): { key: OrderActionKey; icon: string } | null {
  if (o.status === "draft" && o.requires_approval && !o.approved) return { key: "approve", icon: "check" };
  if (o.status === "draft") return { key: "confirm", icon: "checkCircle" };
  if (o.status === "confirmed" || o.status === "partially_delivered") return { key: "deliver", icon: "purchasing" };
  if (o.status === "delivered") return { key: "invoice", icon: "accounting" };
  if (o.status === "invoiced") return { key: "pay", icon: "accounting" };
  return null;
}

function orderFacts(t: TFunction, o: SalesOrder) {
  return [
    { label: t("sales.orders.customer"), value: o.customer_name || o.customer_code },
    { label: t("feedback.fact.amount"), value: formatMinor(o.subtotal_minor + o.tax_minor, o.currency) },
    { label: t("feedback.fact.items"), value: String(o.lines.length) },
    { label: t("feedback.fact.status"), value: t(`sales.status.${o.status}`) },
  ];
}

// Records this action produced — the numbers worth a one-click open (the GL entry of the invoice /
// credit note). Shown in both simple and rich modes.
function orderDocuments(t: TFunction, o: SalesOrder): ReceiptLink[] {
  const docs: ReceiptLink[] = [];
  if (o.invoice_number)
    docs.push({ label: t("feedback.doc.invoice", { no: o.invoice_number }), to: `/go/journal/${encodeURIComponent(o.invoice_number)}` });
  if (o.credit_note_number)
    docs.push({ label: t("feedback.doc.creditNote", { no: o.credit_note_number }), to: `/go/journal/${encodeURIComponent(o.credit_note_number)}` });
  return docs;
}

// Navigation links (rich mode only).
function orderRelated(t: TFunction, o: SalesOrder): ReceiptLink[] {
  return [
    { label: t("feedback.related.customer"), to: `/sales/customers/${encodeURIComponent(o.customer_code)}` },
    { label: t("feedback.related.orders"), to: "/sales" },
  ];
}

/** Build (but don't show) an order receipt for a given event. */
export function orderReceipt(
  t: TFunction,
  o: SalesOrder,
  event: OrderEvent,
  deps: OrderReceiptDeps,
): ActionReceipt {
  const next = nextStep(o);
  const nextAction: ReceiptAction | undefined =
    next && deps.run
      ? { label: t(`feedback.sales.step.${next.key}`), icon: next.icon, run: () => deps.run!(next.key) }
      : undefined;

  const quick: ReceiptAction[] = [];
  if (deps.duplicate) quick.push({ label: t("document.duplicate"), icon: "duplicate", run: deps.duplicate });
  if (deps.print) quick.push({ label: t("document.print"), icon: "print", run: deps.print });
  quick.push({ label: t("feedback.action.newOrder"), icon: "sales", run: () => deps.navigate("/sales/orders/new") });

  return {
    variant: "success",
    title: t(`feedback.sales.order.${event}.title`, { number: o.number }),
    context: t(`feedback.sales.order.${event}.context`, { amount: formatMinor(o.outstanding_minor, o.currency) }),
    next: nextAction,
    documents: orderDocuments(t, o),
    quickActions: quick,
    related: orderRelated(t, o),
    facts: orderFacts(t, o),
  };
}

// --- Deterministic insight engine (async, merged in when ready) ------------------------------

// Stock availability is only meaningful before the goods leave: created / approved / confirmed.
const STOCK_RELEVANT: Partial<Record<OrderEvent, true>> = {
  created: true,
  approved: true,
  confirmed: true,
};

async function stockFindings(t: TFunction, o: SalesOrder): Promise<{ insights: string[]; warnings: string[] }> {
  const soh = await stockOnHand();
  let checked = 0;
  let short = 0;
  for (const line of o.lines) {
    const row = soh.rows.find((r) => r.sku === line.item_sku && r.warehouse_code === o.warehouse_code);
    if (!row) continue; // no balance row ⇒ non-stock / service line — nothing to reserve
    checked++;
    if (Number(row.quantity) < Number(line.quantity)) short++;
  }
  if (checked === 0) return { insights: [], warnings: [] };
  if (short === 0) return { insights: [t("feedback.sales.insight.allInStock")], warnings: [] };
  return {
    insights: [],
    warnings: [short === 1 ? t("feedback.sales.warn.oneShort") : t("feedback.sales.warn.someShort", { count: short })],
  };
}

async function creditFindings(t: TFunction, o: SalesOrder): Promise<{ insights: string[]; warnings: string[] }> {
  const [customers, orders] = await Promise.all([listCustomers(), listOrders()]);
  const cust = customers.find((c) => c.code === o.customer_code);
  if (!cust || cust.credit_limit_minor <= 0) return { insights: [], warnings: [] };
  const used = orders
    .filter((x) => x.customer_code === o.customer_code)
    .reduce((s, x) => s + x.outstanding_minor, 0);
  const pct = Math.round((used / cust.credit_limit_minor) * 100);
  if (pct >= 100) return { insights: [], warnings: [t("feedback.sales.warn.creditExceeded", { pct })] };
  if (pct >= 80) return { insights: [], warnings: [t("feedback.sales.warn.creditHigh", { pct })] };
  return { insights: [t("feedback.sales.insight.creditOk", { pct })], warnings: [] };
}

/**
 * Show an order receipt now, then enrich it with stock/credit findings as they resolve. Lookups are
 * best-effort — a failed insight never disturbs the receipt that's already on screen.
 */
export function showOrderReceipt(
  fb: ActionFeedbackApi,
  t: TFunction,
  o: SalesOrder,
  event: OrderEvent,
  deps: OrderReceiptDeps,
): void {
  const id = fb.show(orderReceipt(t, o, event, deps));

  const jobs: Promise<{ insights: string[]; warnings: string[] }>[] = [creditFindings(t, o)];
  if (STOCK_RELEVANT[event]) jobs.push(stockFindings(t, o));

  void Promise.allSettled(jobs).then((results) => {
    const insights: string[] = [];
    const warnings: string[] = [];
    for (const r of results) {
      if (r.status === "fulfilled") {
        insights.push(...r.value.insights);
        warnings.push(...r.value.warnings);
      }
    }
    if (insights.length || warnings.length) {
      fb.update(id, {
        insights: insights.length ? insights : undefined,
        warnings: warnings.length ? warnings : undefined,
      });
    }
  });
}

// --- Errors: report the blocker AND the way to clear it ---------------------------------------

interface Shortage {
  sku: string;
  /** How much more is needed at the warehouse to cover the undelivered quantity. */
  qty: string;
}

// The stock lines whose remaining-to-deliver quantity exceeds on-hand at the order's warehouse —
// the items that block a delivery, and by how much. A stock item with *no* balance row counts as
// zero on hand (that's exactly the item you're short on); non-stock/service lines are ignored.
// Best-effort; a lookup failure just yields no fix links (the reason still shows).
async function orderShortages(o: SalesOrder): Promise<Shortage[]> {
  const [soh, items] = await Promise.all([stockOnHand(), listItems()]);
  const stockSkus = new Set(items.filter((i) => i.type === "stock").map((i) => i.sku));
  const short: Shortage[] = [];
  for (const line of o.lines) {
    if (!stockSkus.has(line.item_sku)) continue; // service / non-stock: nothing to receive
    const row = soh.rows.find((r) => r.sku === line.item_sku && r.warehouse_code === o.warehouse_code);
    const available = row ? Number(row.quantity) : 0;
    const remaining = Number(line.quantity) - Number(line.delivered_qty || 0);
    const need = remaining - available;
    if (need > 0) short.push({ sku: line.item_sku, qty: String(Number(need.toFixed(4))) });
  }
  return short;
}

// The attempted event → the action key to retry once the blocker is cleared.
const RETRY_KEY: Partial<Record<OrderEvent, OrderActionKey>> = {
  approved: "approve",
  confirmed: "confirm",
  delivered: "deliver",
  invoiced: "invoice",
  paid: "pay",
  returned: "return",
};

/**
 * Show a failed action as a rich error receipt: what went wrong, and one-click links to fix it. For
 * an insufficient-stock delivery, each short item links to the receive-stock form prefilled with
 * that exact item and warehouse — so the block is one click from being cleared, then retried.
 */
export function showOrderError(
  fb: ActionFeedbackApi,
  t: TFunction,
  o: SalesOrder,
  event: OrderEvent,
  error: unknown,
  deps: { run?: (key: OrderActionKey) => void },
): void {
  const rawMessage = error instanceof Error ? error.message : String(error);
  const retryKey = RETRY_KEY[event];
  const next: ReceiptAction | undefined =
    retryKey && deps.run ? { label: t("feedback.sales.action.retry"), icon: "rotate", run: () => deps.run!(retryKey) } : undefined;

  const id = fb.show({
    variant: "error",
    title: t(`feedback.sales.error.${event}.title`, { number: o.number }),
    context: t(`feedback.sales.error.${event}.reason`, { defaultValue: rawMessage }),
    next,
  });

  // A failed delivery is almost always short stock — surface a receive link per short item.
  if (event === "delivered") {
    void orderShortages(o)
      .then((short) => {
        if (!short.length) return;
        fb.update(id, {
          resolutions: short.map((s) => ({
            label: t("feedback.sales.fix.receive", { sku: s.sku, qty: s.qty, warehouse: o.warehouse_code }),
            to: `/inventory/movements?mode=receipt&item=${encodeURIComponent(s.sku)}&warehouse=${encodeURIComponent(o.warehouse_code)}&qty=${encodeURIComponent(s.qty)}`,
          })),
        });
      })
      .catch(() => {});
  }
}

// --- Quotations ------------------------------------------------------------------------------

export type QuoteEvent = "created" | "submitted" | "approved" | "rejected";

export interface QuoteReceiptDeps {
  /** Perform the recommended next step (submit / approve / convert). */
  run?: () => void;
  navigate: (to: string) => void;
  duplicate?: () => void;
}

function nextQuoteStep(q: Quotation): { key: "submit" | "approve" | "convert" } | null {
  if (q.status === "draft") return { key: "submit" };
  if (q.status === "submitted") return { key: "approve" };
  if (q.status === "approved") return { key: "convert" };
  return null;
}

export function showQuotationReceipt(
  fb: ActionFeedbackApi,
  t: TFunction,
  q: Quotation,
  event: QuoteEvent,
  deps: QuoteReceiptDeps,
): void {
  const next = nextQuoteStep(q);
  const nextAction: ReceiptAction | undefined =
    next && deps.run ? { label: t(`feedback.sales.quoteStep.${next.key}`), icon: "checkCircle", run: deps.run } : undefined;

  const quick: ReceiptAction[] = [];
  if (deps.duplicate) quick.push({ label: t("document.duplicate"), icon: "duplicate", run: deps.duplicate });
  quick.push({ label: t("feedback.action.newQuote"), icon: "sales", run: () => deps.navigate("/sales/quotations/new") });

  const documents: ReceiptLink[] = q.converted_order_number
    ? [{ label: t("feedback.doc.order", { no: q.converted_order_number }), to: `/go/sales_order/${encodeURIComponent(q.converted_order_number)}` }]
    : [];

  fb.show({
    variant: event === "rejected" ? "info" : "success",
    title: t(`feedback.sales.quote.${event}.title`, { number: q.number }),
    context: t(`feedback.sales.quote.${event}.context`),
    next: nextAction,
    documents,
    quickActions: quick,
    related: [
      { label: t("feedback.related.customer"), to: `/sales/customers/${encodeURIComponent(q.customer_code)}` },
      { label: t("feedback.related.quotations"), to: "/sales/quotations" },
    ],
    facts: [
      { label: t("sales.orders.customer"), value: q.customer_name || q.customer_code },
      { label: t("feedback.fact.amount"), value: formatMinor(q.subtotal_minor, q.currency) },
      { label: t("feedback.fact.items"), value: String(q.lines.length) },
      { label: t("feedback.fact.status"), value: t(`sales.quotationStatus.${q.status}`) },
    ],
  });
}

// --- Customers -------------------------------------------------------------------------------

export function showCustomerReceipt(
  fb: ActionFeedbackApi,
  t: TFunction,
  customer: { code: string; name: string },
  deps: { navigate: (to: string) => void },
): void {
  fb.show({
    variant: "success",
    title: t("feedback.sales.customer.created.title", { name: customer.name }),
    context: t("feedback.sales.customer.created.context"),
    next: {
      label: t("feedback.action.newOrderFor"),
      icon: "sales",
      run: () => deps.navigate("/sales/orders/new"),
    },
    related: [
      { label: t("feedback.related.customer"), to: `/sales/customers/${encodeURIComponent(customer.code)}` },
      { label: t("feedback.related.customers"), to: "/sales/customers" },
    ],
    facts: [{ label: t("sales.orders.customer"), value: customer.name || customer.code }],
  });
}
