// Typed wrappers for the sales API (/api/sales/*). Prices/values are integer minor units.
import { apiFetch } from "./client";
import type { StageHistoryEntry } from "../lib/workflow";

export type OrderStatus =
  | "draft"
  | "confirmed"
  | "partially_delivered"
  | "delivered"
  | "invoiced"
  | "paid"
  | "returned"
  | "cancelled";

export interface Customer {
  id: string;
  code: string;
  name: string;
  credit_limit_minor: number;
  is_active: boolean;
}

export interface OrderLine {
  line_no: number;
  item_sku: string;
  description: string;
  quantity: string;
  delivered_qty: string;
  returned_qty: string;
  unit_price_minor: number;
  discount_minor: number;
  line_total_minor: number;
}

export interface SalesOrder {
  id: string;
  number: string;
  customer_code: string;
  customer_name: string;
  order_date: string;
  warehouse_code: string;
  currency: string;
  status: OrderStatus;
  subtotal_minor: number;
  tax_code: string;
  tax_minor: number;
  invoiced_minor: number;
  paid_minor: number;
  returned_minor: number;
  outstanding_minor: number;
  approved: boolean;
  requires_approval: boolean;
  invoice_number: string;
  credit_note_number: string;
  notes: string;
  lines: OrderLine[];
}

export function listCustomers(): Promise<Customer[]> {
  return apiFetch<Customer[]>("/sales/customers");
}

export function createCustomer(payload: {
  code: string;
  name: string;
  credit_limit_minor?: number;
}): Promise<Customer> {
  return apiFetch<Customer>("/sales/customers", { method: "POST", body: JSON.stringify(payload) });
}

export function listOrders(status?: OrderStatus): Promise<SalesOrder[]> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<SalesOrder[]>(`/sales/orders${qs}`);
}

export function getOrder(id: string): Promise<SalesOrder> {
  return apiFetch<SalesOrder>(`/sales/orders/${id}`);
}

export function getOrderHistory(id: string): Promise<StageHistoryEntry[]> {
  return apiFetch<StageHistoryEntry[]>(`/sales/orders/${id}/history`);
}

export interface NewOrderLine {
  item_sku: string;
  quantity: string;
  unit_price: number;
  discount?: number;
  description?: string;
}

export function createOrder(payload: {
  customer_code: string;
  warehouse_code: string;
  order_date?: string;
  notes?: string;
  tax_code?: string;
  lines: NewOrderLine[];
}): Promise<SalesOrder> {
  return apiFetch<SalesOrder>("/sales/orders", { method: "POST", body: JSON.stringify(payload) });
}

const action = (id: string, name: string) =>
  apiFetch<SalesOrder>(`/sales/orders/${id}/${name}`, { method: "POST", body: "{}" });

export const approveOrder = (id: string) => action(id, "approve");
export const confirmOrder = (id: string) => action(id, "confirm");
export const deliverOrder = (id: string) => action(id, "deliver");
export const invoiceOrder = (id: string) => action(id, "invoice");
export const returnOrder = (id: string) => action(id, "return");
export const cancelOrder = (id: string) => action(id, "cancel");
// Fast-path the same-day counter sale: confirm → deliver → invoice in one move (server-side, atomic).
export const completeSale = (id: string) => action(id, "complete");

export function payOrder(id: string, amount: number): Promise<SalesOrder> {
  return apiFetch<SalesOrder>(`/sales/orders/${id}/payment`, {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
}

// --- Quotations ------------------------------------------------------------------------------

export type QuotationStatus =
  | "draft"
  | "submitted"
  | "approved"
  | "rejected"
  | "converted"
  | "cancelled";

export interface QuotationLine {
  line_no: number;
  item_sku: string;
  description: string;
  quantity: string;
  unit_price_minor: number;
  line_total_minor: number;
}

export interface Quotation {
  id: string;
  number: string;
  customer_code: string;
  customer_name: string;
  quote_date: string;
  warehouse_code: string;
  currency: string;
  status: QuotationStatus;
  subtotal_minor: number;
  requires_approval: boolean;
  rejected_reason: string;
  converted_order_number: string;
  notes: string;
  lines: QuotationLine[];
}

export interface ConvertResult {
  quotation: Quotation;
  order_id: string;
  order_number: string;
}

export function listQuotations(status?: QuotationStatus): Promise<Quotation[]> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<Quotation[]>(`/sales/quotations${qs}`);
}

export function getQuotation(id: string): Promise<Quotation> {
  return apiFetch<Quotation>(`/sales/quotations/${id}`);
}

export function createQuotation(payload: {
  customer_code: string;
  warehouse_code: string;
  notes?: string;
  lines: NewOrderLine[];
}): Promise<Quotation> {
  return apiFetch<Quotation>("/sales/quotations", { method: "POST", body: JSON.stringify(payload) });
}

const quoteAction = (id: string, name: string) =>
  apiFetch<Quotation>(`/sales/quotations/${id}/${name}`, { method: "POST", body: "{}" });

export const submitQuotation = (id: string) => quoteAction(id, "submit");
export const approveQuotation = (id: string) => quoteAction(id, "approve");

export function rejectQuotation(id: string, reason: string): Promise<Quotation> {
  return apiFetch<Quotation>(`/sales/quotations/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function convertQuotation(id: string): Promise<ConvertResult> {
  return apiFetch<ConvertResult>(`/sales/quotations/${id}/convert`, { method: "POST", body: "{}" });
}
