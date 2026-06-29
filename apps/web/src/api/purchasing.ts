// Typed wrappers for the purchasing API (/api/purchasing/*). Costs/values are integer minor units.
import { apiFetch } from "./client";
import type { StageHistoryEntry } from "../lib/workflow";

export type POStatus =
  | "draft"
  | "confirmed"
  | "partially_received"
  | "received"
  | "billed"
  | "paid"
  | "returned"
  | "cancelled";

export interface Supplier {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface POLine {
  line_no: number;
  item_sku: string;
  description: string;
  quantity: string;
  received_qty: string;
  returned_qty: string;
  unit_cost_minor: number;
  line_total_minor: number;
}

export interface PurchaseOrder {
  id: string;
  number: string;
  supplier_code: string;
  supplier_name: string;
  order_date: string;
  warehouse_code: string;
  currency: string;
  status: POStatus;
  tax_code: string;
  subtotal_minor: number;
  received_minor: number;
  tax_minor: number;
  billed_minor: number;
  paid_minor: number;
  returned_minor: number;
  outstanding_minor: number;
  approved: boolean;
  requires_approval: boolean;
  bill_number: string;
  debit_note_number: string;
  notes: string;
  lines: POLine[];
}

export function listSuppliers(): Promise<Supplier[]> {
  return apiFetch<Supplier[]>("/purchasing/suppliers");
}

export function createSupplier(payload: { code: string; name: string }): Promise<Supplier> {
  return apiFetch<Supplier>("/purchasing/suppliers", { method: "POST", body: JSON.stringify(payload) });
}

export function listPurchaseOrders(status?: POStatus): Promise<PurchaseOrder[]> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<PurchaseOrder[]>(`/purchasing/orders${qs}`);
}

export function getPurchaseOrder(id: string): Promise<PurchaseOrder> {
  return apiFetch<PurchaseOrder>(`/purchasing/orders/${id}`);
}

export function getPurchaseOrderHistory(id: string): Promise<StageHistoryEntry[]> {
  return apiFetch<StageHistoryEntry[]>(`/purchasing/orders/${id}/history`);
}

export interface NewPOLine {
  item_sku: string;
  quantity: string;
  unit_cost: number;
  description?: string;
}

export function createPurchaseOrder(payload: {
  supplier_code: string;
  warehouse_code: string;
  order_date?: string;
  tax_code?: string;
  notes?: string;
  lines: NewPOLine[];
}): Promise<PurchaseOrder> {
  return apiFetch<PurchaseOrder>("/purchasing/orders", { method: "POST", body: JSON.stringify(payload) });
}

const action = (id: string, name: string) =>
  apiFetch<PurchaseOrder>(`/purchasing/orders/${id}/${name}`, { method: "POST", body: "{}" });

export const approvePO = (id: string) => action(id, "approve");
export const confirmPO = (id: string) => action(id, "confirm");
export const receivePO = (id: string) => action(id, "receive");
export const billPO = (id: string) => action(id, "bill");
export const returnPO = (id: string) => action(id, "return");

export function payPO(id: string, amount: number): Promise<PurchaseOrder> {
  return apiFetch<PurchaseOrder>(`/purchasing/orders/${id}/payment`, {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
}

// --- Purchase requests -----------------------------------------------------------------------

export type PRStatus =
  | "draft"
  | "submitted"
  | "approved"
  | "rejected"
  | "converted"
  | "cancelled";

export interface RequestLine {
  line_no: number;
  item_sku: string;
  description: string;
  quantity: string;
  unit_cost_minor: number;
  line_total_minor: number;
}

export interface PurchaseRequest {
  id: string;
  number: string;
  supplier_code: string;
  supplier_name: string;
  request_date: string;
  warehouse_code: string;
  currency: string;
  status: PRStatus;
  subtotal_minor: number;
  requires_approval: boolean;
  rejected_reason: string;
  converted_order_number: string;
  notes: string;
  lines: RequestLine[];
}

export interface PRConvertResult {
  request: PurchaseRequest;
  order_id: string;
  order_number: string;
}

export function listRequests(status?: PRStatus): Promise<PurchaseRequest[]> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<PurchaseRequest[]>(`/purchasing/requests${qs}`);
}

export function getRequest(id: string): Promise<PurchaseRequest> {
  return apiFetch<PurchaseRequest>(`/purchasing/requests/${id}`);
}

export function createRequest(payload: {
  supplier_code: string;
  warehouse_code: string;
  notes?: string;
  lines: NewPOLine[];
}): Promise<PurchaseRequest> {
  return apiFetch<PurchaseRequest>("/purchasing/requests", { method: "POST", body: JSON.stringify(payload) });
}

const reqAction = (id: string, name: string) =>
  apiFetch<PurchaseRequest>(`/purchasing/requests/${id}/${name}`, { method: "POST", body: "{}" });

export const submitRequest = (id: string) => reqAction(id, "submit");
export const approveRequest = (id: string) => reqAction(id, "approve");

export function rejectRequest(id: string, reason: string): Promise<PurchaseRequest> {
  return apiFetch<PurchaseRequest>(`/purchasing/requests/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function convertRequest(id: string): Promise<PRConvertResult> {
  return apiFetch<PRConvertResult>(`/purchasing/requests/${id}/convert`, { method: "POST", body: "{}" });
}
