import { apiFetch } from "./client";

export interface ChartOfAccountsState {
  seeded: boolean;
  accounts: number;
}

export interface SetupStatus {
  is_setup_complete: boolean;
  chart_of_accounts: ChartOfAccountsState;
}

/** Whether first-run setup is done + per-step state — the post-login route guard reads this. */
export function getSetupStatus(): Promise<SetupStatus> {
  return apiFetch<SetupStatus>("/setup/status");
}

/** Provision the baseline chart of accounts in one call (System Admin only). */
export function seedChartOfAccounts(): Promise<ChartOfAccountsState> {
  return apiFetch<ChartOfAccountsState>("/setup/chart-of-accounts", { method: "POST" });
}

/** Mark first-run setup finished (System Admin only). */
export function completeSetup(): Promise<SetupStatus> {
  return apiFetch<SetupStatus>("/setup/complete", { method: "POST" });
}
