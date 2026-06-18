// Typed wrappers for the CRM API (/api/crm/*). Amounts are integer minor units.
import { apiFetch } from "./client";

export type LeadStatus = "new" | "contacted" | "qualified" | "unqualified" | "converted";
export type OppStage = "qualifying" | "proposal" | "negotiation" | "won" | "lost";
export type TicketPriority = "low" | "medium" | "high" | "urgent";
export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";
export type ActivityType = "call" | "email" | "meeting" | "task" | "note";
export type RelatedType = "lead" | "opportunity" | "ticket";
export type CampaignChannel = "email" | "web" | "call" | "event" | "social" | "other";
export type CampaignStatus = "draft" | "active" | "completed";

export interface CampaignMetrics {
  lead_count: number;
  opportunity_count: number;
  won_count: number;
  open_pipeline_minor: number;
  won_value_minor: number;
  roi_minor: number;
  is_profitable: boolean;
}

export interface Campaign {
  id: string;
  code: string;
  name: string;
  channel: CampaignChannel;
  status: CampaignStatus;
  start_date: string | null;
  end_date: string | null;
  cost_minor: number;
  notes: string;
  metrics?: CampaignMetrics;
}

export interface Lead {
  id: string;
  code: string;
  name: string;
  company: string;
  email: string;
  phone: string;
  source: string;
  status: LeadStatus;
  owner: string;
  notes: string;
}

export interface OppLine {
  line_no: number;
  item_sku: string;
  description: string;
  quantity: string;
  unit_price_minor: number;
  line_total_minor: number;
}

export interface Opportunity {
  id: string;
  number: string;
  name: string;
  lead_code: string;
  customer_code: string;
  warehouse_code: string;
  stage: OppStage;
  currency: string;
  amount_minor: number;
  weighted_minor: number;
  probability: number;
  expected_close: string | null;
  sales_order_number: string;
  notes: string;
  lines: OppLine[];
}

export interface Ticket {
  id: string;
  number: string;
  customer_code: string;
  subject: string;
  description: string;
  priority: TicketPriority;
  status: TicketStatus;
  owner: string;
  opened_at: string;
  sla_due_at: string;
  resolved_at: string | null;
  escalated_at: string | null;
  is_breached: boolean;
  is_escalated: boolean;
}

export interface Activity {
  id: string;
  type: ActivityType;
  subject: string;
  related_type: RelatedType;
  related_ref: string;
  owner: string;
  due_date: string | null;
  done: boolean;
  notes: string;
}

// --- Campaigns ---
export function listCampaigns(): Promise<Campaign[]> {
  return apiFetch<Campaign[]>("/crm/campaigns");
}

export function getCampaign(id: string): Promise<Campaign> {
  return apiFetch<Campaign>(`/crm/campaigns/${id}`);
}

export function createCampaign(payload: {
  code: string;
  name: string;
  channel?: CampaignChannel;
  cost_minor?: number;
}): Promise<Campaign> {
  return apiFetch<Campaign>("/crm/campaigns", { method: "POST", body: JSON.stringify(payload) });
}

export function setCampaignStatus(id: string, status: CampaignStatus): Promise<Campaign> {
  return apiFetch<Campaign>(`/crm/campaigns/${id}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

// --- Leads ---
export function listLeads(status?: LeadStatus): Promise<Lead[]> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<Lead[]>(`/crm/leads${qs}`);
}

export function createLead(payload: {
  name: string;
  company?: string;
  email?: string;
  phone?: string;
  source?: string;
  campaign_code?: string;
}): Promise<Lead> {
  return apiFetch<Lead>("/crm/leads", { method: "POST", body: JSON.stringify(payload) });
}

export function setLeadStatus(id: string, status: LeadStatus): Promise<Lead> {
  return apiFetch<Lead>(`/crm/leads/${id}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

export function convertLead(
  id: string,
  payload: { opportunity_name?: string; customer_code?: string },
): Promise<Opportunity> {
  return apiFetch<Opportunity>(`/crm/leads/${id}/convert`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- Opportunities ---
export interface NewOppLine {
  item_sku: string;
  quantity: string;
  unit_price: number;
  description?: string;
}

export function listOpportunities(stage?: OppStage): Promise<Opportunity[]> {
  const qs = stage ? `?stage=${stage}` : "";
  return apiFetch<Opportunity[]>(`/crm/opportunities${qs}`);
}

export function getOpportunity(id: string): Promise<Opportunity> {
  return apiFetch<Opportunity>(`/crm/opportunities/${id}`);
}

export function createOpportunity(payload: {
  name: string;
  customer_code?: string;
  warehouse_code?: string;
  campaign_code?: string;
  probability?: number;
  lines?: NewOppLine[];
}): Promise<Opportunity> {
  return apiFetch<Opportunity>("/crm/opportunities", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function advanceStage(id: string, stage: OppStage): Promise<Opportunity> {
  return apiFetch<Opportunity>(`/crm/opportunities/${id}/stage`, {
    method: "POST",
    body: JSON.stringify({ stage }),
  });
}

export function winOpportunity(id: string, createSalesOrder = true): Promise<Opportunity> {
  return apiFetch<Opportunity>(`/crm/opportunities/${id}/win`, {
    method: "POST",
    body: JSON.stringify({ create_sales_order: createSalesOrder }),
  });
}

export function loseOpportunity(id: string, reason = ""): Promise<Opportunity> {
  return apiFetch<Opportunity>(`/crm/opportunities/${id}/lose`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

// --- Tickets ---
export function listTickets(status?: TicketStatus): Promise<Ticket[]> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<Ticket[]>(`/crm/tickets${qs}`);
}

export function createTicket(payload: {
  subject: string;
  customer_code?: string;
  description?: string;
  priority?: TicketPriority;
}): Promise<Ticket> {
  return apiFetch<Ticket>("/crm/tickets", { method: "POST", body: JSON.stringify(payload) });
}

const ticketAction = (id: string, name: string, body = "{}") =>
  apiFetch<Ticket>(`/crm/tickets/${id}/${name}`, { method: "POST", body });

export const startTicket = (id: string) => ticketAction(id, "start");
export const resolveTicket = (id: string) => ticketAction(id, "resolve");
export const closeTicket = (id: string) => ticketAction(id, "close");
export const escalateTicket = (id: string) => ticketAction(id, "escalate");

export function runEscalations(): Promise<{ escalated: string[]; count: number }> {
  return apiFetch<{ escalated: string[]; count: number }>("/crm/tickets-run-escalations", {
    method: "POST",
    body: "{}",
  });
}

// --- Activities ---
export function listActivities(relatedType?: RelatedType, relatedRef?: string): Promise<Activity[]> {
  const params = new URLSearchParams();
  if (relatedType) params.set("related_type", relatedType);
  if (relatedRef) params.set("related_ref", relatedRef);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<Activity[]>(`/crm/activities${qs}`);
}

export function logActivity(payload: {
  type: ActivityType;
  subject: string;
  related_type: RelatedType;
  related_ref: string;
}): Promise<Activity> {
  return apiFetch<Activity>("/crm/activities", { method: "POST", body: JSON.stringify(payload) });
}

export function completeActivity(id: string): Promise<Activity> {
  return apiFetch<Activity>(`/crm/activities/${id}/complete`, { method: "POST", body: "{}" });
}
