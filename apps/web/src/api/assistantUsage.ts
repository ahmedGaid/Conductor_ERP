// AI usage & cost read endpoint (twenty-harvest FILE_20 Task B): straight aggregation over the
// same Trace/Budget/SpendRollup records api/assistantOps.ts already reads for the ops view.
import { apiFetch } from "./client";

export interface UsageTotals {
  requests: number;
  input_tokens: number;
  output_tokens: number;
  cost_microcents: number;
  cache_hit_share: number;
  degraded_minutes: number;
}

export interface UsageByProvider {
  provider: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  cost_microcents: number;
}

export interface UsageByUser {
  user_id: number;
  username: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  cost_microcents: number;
}

export interface UsageBudgetScope {
  limit_microcents: number | null;
  action: "block" | "notify" | null;
}

export interface UsageBudget {
  request: UsageBudgetScope;
  user_daily: UsageBudgetScope;
  org: UsageBudgetScope & { consumed_microcents: number };
}

export interface UsageMonth {
  month: string;
  totals: UsageTotals;
  by_provider: UsageByProvider[];
  by_user: UsageByUser[];
  budget: UsageBudget;
}

export function getAssistantUsage(month?: string): Promise<UsageMonth> {
  const q = month ? `?month=${month}` : "";
  return apiFetch<UsageMonth>(`/assistant/usage${q}`);
}
