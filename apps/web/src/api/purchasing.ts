// Typed wrappers for the purchasing API (/api/purchasing/*). Costs/values are integer minor units.
import { apiFetch } from "./client";

export type POStatus = "draft" | "confirmed" | "received" | "billed" | "paid" | "cancelled";

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
  subtotal_minor: number;
  received_minor: number;
  billed_minor: number;
  paid_minor: number;
  outstanding_minor: number;
  bill_number: string;
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
  notes?: string;
  lines: NewPOLine[];
}): Promise<PurchaseOrder> {
  return apiFetch<PurchaseOrder>("/purchasing/orders", { method: "POST", body: JSON.stringify(payload) });
}

const action = (id: string, name: string) =>
  apiFetch<PurchaseOrder>(`/purchasing/orders/${id}/${name}`, { method: "POST", body: "{}" });

export const confirmPO = (id: string) => action(id, "confirm");
export const receivePO = (id: string) => action(id, "receive");
export const billPO = (id: string) => action(id, "bill");

export function payPO(id: string, amount: number): Promise<PurchaseOrder> {
  return apiFetch<PurchaseOrder>(`/purchasing/orders/${id}/payment`, {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
}
