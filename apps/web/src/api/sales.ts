// Typed wrappers for the sales API (/api/sales/*). Prices/values are integer minor units.
import { apiFetch } from "./client";

export type OrderStatus = "draft" | "confirmed" | "delivered" | "invoiced" | "paid" | "cancelled";

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
  unit_price_minor: number;
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
  invoiced_minor: number;
  paid_minor: number;
  outstanding_minor: number;
  invoice_number: string;
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

export interface NewOrderLine {
  item_sku: string;
  quantity: string;
  unit_price: number;
  description?: string;
}

export function createOrder(payload: {
  customer_code: string;
  warehouse_code: string;
  order_date?: string;
  notes?: string;
  lines: NewOrderLine[];
}): Promise<SalesOrder> {
  return apiFetch<SalesOrder>("/sales/orders", { method: "POST", body: JSON.stringify(payload) });
}

const action = (id: string, name: string) =>
  apiFetch<SalesOrder>(`/sales/orders/${id}/${name}`, { method: "POST", body: "{}" });

export const confirmOrder = (id: string) => action(id, "confirm");
export const deliverOrder = (id: string) => action(id, "deliver");
export const invoiceOrder = (id: string) => action(id, "invoice");

export function payOrder(id: string, amount: number): Promise<SalesOrder> {
  return apiFetch<SalesOrder>(`/sales/orders/${id}/payment`, {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
}
