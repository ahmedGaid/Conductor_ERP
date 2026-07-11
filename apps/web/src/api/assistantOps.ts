// Ops view (ai-reliability T1.8): admin-only — what the AI did, what it cost, whether it's
// healthy. Reads Trace/TraceStep rows the tracing seam (services/tracing.py) already writes for
// every provider call. Kept out of api/assistant.ts (which loads eagerly with the app shell) since
// this only ever loads inside OpsPage's own route-split chunk.
import { apiFetch } from "./client";

export interface OpsDailyCount {
  date: string;
  count: number;
  by_feature: Record<string, number>;
}

export interface OpsErrorClassCount {
  error_class: string;
  count: number;
}

export interface OpsEvalScoreboard {
  date: string;
  pass_rate: number | null;
  pass: number;
  fail: number;
  needs_judge: number;
  error: number;
}

export interface OpsSummary {
  days: number;
  total_calls: number;
  error_rate: number;
  daily: OpsDailyCount[];
  latency_ms: { p50: number; p95: number };
  ttft_ms: { p50: number; p95: number };
  input_tokens: number;
  output_tokens: number;
  // Provider cost, integer microcents (1e-6 of a currency cent) — same money discipline as the
  // ERP ledger, just a finer unit since per-call cost is fractions of a cent.
  cost_microcents: number;
  top_error_classes: OpsErrorClassCount[];
  // Exact-match response cache (T2.5): lookups = calls on cache-enabled task classes; a hit is
  // a call answered at cost 0 from the cache.
  cache: { lookups: number; hits: number; hit_rate: number };
  eval_scoreboard: OpsEvalScoreboard | null;
}

export function getOpsSummary(days = 7): Promise<OpsSummary> {
  return apiFetch<OpsSummary>(`/assistant/ops/summary?days=${days}`);
}

export interface OpsTraceStep {
  seq: number;
  kind: "llm" | "tool" | "retrieval" | "guardrail" | "validation";
  name: string;
  latency_ms: number;
  ok: boolean;
  detail: Record<string, unknown>;
}

// A gateway routing decision (ai-reliability T2.3): the failover chain tried, which provider
// answered, and why any provider was skipped (breaker-open, or a specific error class).
export interface OpsTraceRouting {
  chain: string[];
  chosen: string | null;
  skipped: { provider: string; reason: string }[];
}

export interface OpsTrace {
  id: string;
  created_at: string;
  feature: string;
  actor: { id: number; username: string } | null;
  provider: string;
  model: string;
  prompt_ref: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
  cost_microcents: number;
  status: "ok" | "error" | "timeout" | "cancelled" | "guardrail_blocked";
  error_class: string;
  meta: { routing?: OpsTraceRouting } & Record<string, unknown>;
  steps: OpsTraceStep[];
}

export interface OpsTracePage {
  count: number;
  page: number;
  page_size: number;
  results: OpsTrace[];
}

export function listOpsTraces(params: {
  days?: number;
  feature?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<OpsTracePage> {
  const q = new URLSearchParams();
  if (params.days) q.set("days", String(params.days));
  if (params.feature) q.set("feature", params.feature);
  if (params.status) q.set("status", params.status);
  if (params.page) q.set("page", String(params.page));
  if (params.page_size) q.set("page_size", String(params.page_size));
  return apiFetch<OpsTracePage>(`/assistant/ops/traces?${q.toString()}`);
}
