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
  poll_stalled: boolean;
}

export function listETAInvoices(status?: ETAStatus): Promise<ETAInvoice[]> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<ETAInvoice[]>(`/einvoice/invoices${qs}`);
}

const action = (id: string, name: string) =>
  apiFetch<ETAInvoice>(`/einvoice/invoices/${id}/${name}`, { method: "POST", body: "{}" });

export const submitETAInvoice = (id: string) => action(id, "submit");
export const pollETAInvoice = (id: string) => action(id, "poll");

// --- ETA connection configuration (admin-only, Settings → E-Invoicing) ---
// The client secret is write-only: sent up on save, never returned. `has_secret` reports presence.

export type ETAConfigSource = "database" | "environment" | "none";

export interface ETAConfig {
  environment: "" | "sandbox" | "production";
  identity_url: string;
  api_base_url: string;
  client_id: string;
  rin: string;
  enabled: boolean;
  has_secret: boolean;
  last_test_ok_at: string | null;
  source: ETAConfigSource;
  configured: boolean;
  missing: string[];
  simulated: boolean;
}

// Fields the admin can write. `client_secret` empty = leave stored one unchanged; `clear_secret`
// removes it. Everything is optional so a partial save (e.g. just toggling `enabled`) is one call.
export interface ETAConfigUpdate {
  environment?: "" | "sandbox" | "production";
  identity_url?: string;
  api_base_url?: string;
  client_id?: string;
  rin?: string;
  client_secret?: string;
  clear_secret?: boolean;
  enabled?: boolean;
}

export interface ETATestResult {
  ok: boolean;
  reason: "ok" | "not_configured" | "auth_failed";
  detail: string;
}

export const getETAConfig = () => apiFetch<ETAConfig>("/einvoice/config");

export const saveETAConfig = (changes: ETAConfigUpdate) =>
  apiFetch<ETAConfig>("/einvoice/config", { method: "PUT", body: JSON.stringify(changes) });

export const testETAConnection = () =>
  apiFetch<ETATestResult>("/einvoice/config/test", { method: "POST", body: "{}" });
