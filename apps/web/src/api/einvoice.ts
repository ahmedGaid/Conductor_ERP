// Typed wrappers for the e-invoicing API (/api/einvoice/*). Amounts are integer minor units.
import { apiFetch } from "./client";

export type ETAStatus = "draft" | "submitted" | "valid" | "rejected" | "cancelled";

export interface ETAInvoice {
  id: string;
  invoice_number: string;
  order_number: string;
  customer_code: string;
  customer_name: string;
  issue_date: string;
  currency: string;
  tax_code: string;
  net_minor: number;
  tax_minor: number;
  total_minor: number;
  status: ETAStatus;
  uuid: string;
  document_hash: string;
  error_text: string;
}

export function listETAInvoices(status?: ETAStatus): Promise<ETAInvoice[]> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<ETAInvoice[]>(`/einvoice/invoices${qs}`);
}

const action = (id: string, name: string) =>
  apiFetch<ETAInvoice>(`/einvoice/invoices/${id}/${name}`, { method: "POST", body: "{}" });

export const submitETAInvoice = (id: string) => action(id, "submit");
export const pollETAInvoice = (id: string) => action(id, "poll");
