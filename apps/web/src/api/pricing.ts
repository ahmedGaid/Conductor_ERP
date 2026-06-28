// Typed wrappers for the pricing API (/api/pricing/*).
// Prices are integer minor units in the price list's currency; quantities are decimal strings.
import { apiFetch } from "./client";

export interface PriceList {
  id: string;
  code: string;
  name: string;
  currency: string;
  tax_inclusive: boolean;
  is_default: boolean;
  is_active: boolean;
  line_count: number;
}

export interface PriceListLine {
  id: string;
  item_sku: string;
  uom: string;
  unit_price_minor: number;
  min_quantity: string;
  valid_from: string | null;
  valid_to: string | null;
}

export interface PriceResolution {
  unit_price_minor: number;
  source: "customer_item" | "customer_list" | "default_list";
  price_list_code: string | null;
  tax_inclusive: boolean;
}

/** A customer's default price list (one per customer). */
export interface CustomerAssignment {
  id: string;
  customer_code: string;
  price_list_code: string;
}

/** A negotiated per-customer item price — the highest-precedence override. */
export interface CustomerItemPrice {
  id: string;
  customer_code: string;
  item_sku: string;
  uom: string;
  unit_price_minor: number;
  tax_inclusive: boolean;
  min_quantity: string;
  valid_from: string | null;
  valid_to: string | null;
}

export function listPriceLists(): Promise<PriceList[]> {
  return apiFetch<PriceList[]>("/pricing/price-lists");
}

export function createPriceList(payload: {
  code: string;
  name: string;
  currency?: string;
  tax_inclusive?: boolean;
  is_default?: boolean;
}): Promise<PriceList> {
  return apiFetch<PriceList>("/pricing/price-lists", { method: "POST", body: JSON.stringify(payload) });
}

export function getPriceList(id: string): Promise<PriceList> {
  return apiFetch<PriceList>(`/pricing/price-lists/${id}`);
}

export function updatePriceList(
  id: string,
  changes: Partial<Pick<PriceList, "name" | "currency" | "tax_inclusive" | "is_default" | "is_active">>,
): Promise<PriceList> {
  return apiFetch<PriceList>(`/pricing/price-lists/${id}`, { method: "PATCH", body: JSON.stringify(changes) });
}

export function listLines(listId: string): Promise<PriceListLine[]> {
  return apiFetch<PriceListLine[]>(`/pricing/price-lists/${listId}/lines`);
}

export function addLine(
  listId: string,
  payload: {
    item_sku: string;
    unit_price_minor: number;
    uom?: string;
    min_quantity?: string;
    valid_from?: string | null;
    valid_to?: string | null;
  },
): Promise<PriceListLine> {
  return apiFetch<PriceListLine>(`/pricing/price-lists/${listId}/lines`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateLine(lineId: string, changes: Partial<PriceListLine>): Promise<PriceListLine> {
  return apiFetch<PriceListLine>(`/pricing/lines/${lineId}`, { method: "PATCH", body: JSON.stringify(changes) });
}

export function deleteLine(lineId: string): Promise<void> {
  return apiFetch<void>(`/pricing/lines/${lineId}`, { method: "DELETE" });
}

// ── Customer → price-list assignments (P5) ──────────────────────────────────────────────────────────
export function listAssignments(): Promise<CustomerAssignment[]> {
  return apiFetch<CustomerAssignment[]>("/pricing/customer-assignments");
}

/** Upsert a customer's price-list assignment (one per customer — re-assigning moves them). */
export function setAssignment(payload: {
  customer_code: string;
  price_list_code: string;
}): Promise<CustomerAssignment> {
  return apiFetch<CustomerAssignment>("/pricing/customer-assignments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteAssignment(id: string): Promise<void> {
  return apiFetch<void>(`/pricing/customer-assignments/${id}`, { method: "DELETE" });
}

// ── Per-customer item overrides (P5) ────────────────────────────────────────────────────────────────
export function listCustomerPrices(): Promise<CustomerItemPrice[]> {
  return apiFetch<CustomerItemPrice[]>("/pricing/customer-prices");
}

export function addCustomerPrice(payload: {
  customer_code: string;
  item_sku: string;
  unit_price_minor: number;
  uom?: string;
  tax_inclusive?: boolean;
  min_quantity?: string;
  valid_from?: string | null;
  valid_to?: string | null;
}): Promise<CustomerItemPrice> {
  return apiFetch<CustomerItemPrice>("/pricing/customer-prices", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteCustomerPrice(id: string): Promise<void> {
  return apiFetch<void>(`/pricing/customer-prices/${id}`, { method: "DELETE" });
}

/** Resolve the best net unit price for a customer+item — used to prefill order/quotation lines (P3). */
export function resolvePrice(params: {
  customer: string;
  sku: string;
  qty?: string;
  taxCode?: string;
  currency?: string;
}): Promise<PriceResolution | null> {
  const q = new URLSearchParams({ customer: params.customer, sku: params.sku });
  if (params.qty) q.set("qty", params.qty);
  if (params.taxCode) q.set("tax_code", params.taxCode);
  if (params.currency) q.set("currency", params.currency);
  return apiFetch<PriceResolution | null>(`/pricing/resolve?${q.toString()}`);
}
