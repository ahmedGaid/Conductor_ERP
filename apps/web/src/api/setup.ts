import { apiFetch } from "./client";

export interface ChartOfAccountsState {
  seeded: boolean;
  accounts: number;
}

export interface TaxState {
  vat_rate_bps: number;
  einvoice_enabled: boolean;
}

export interface SetupStatus {
  is_setup_complete: boolean;
  chart_of_accounts: ChartOfAccountsState;
  tax: TaxState;
  /** Roles the invite-team step offers in its picker. */
  available_roles: string[];
}

/** A team member created by the invite step — carries the one-time temporary password. */
export interface InvitedUser {
  id: number;
  username: string;
  email: string;
  role: string | null;
  temp_password: string;
}

/** Whether first-run setup is done + per-step state — the post-login route guard reads this. */
export function getSetupStatus(): Promise<SetupStatus> {
  return apiFetch<SetupStatus>("/setup/status");
}

/** Provision the baseline chart of accounts in one call (System Admin only). */
export function seedChartOfAccounts(): Promise<ChartOfAccountsState> {
  return apiFetch<ChartOfAccountsState>("/setup/chart-of-accounts", { method: "POST" });
}

/** Set the standard VAT rate and/or the e-invoicing toggle (System Admin only). */
export function setTaxSettings(changes: Partial<TaxState>): Promise<TaxState> {
  return apiFetch<TaxState>("/setup/tax", { method: "POST", body: JSON.stringify(changes) });
}

/** Invite a team member with a role (System Admin only). Returns their temp password once. */
export function inviteTeamMember(body: {
  username: string;
  email: string;
  role?: string;
}): Promise<InvitedUser> {
  return apiFetch<InvitedUser>("/setup/users", { method: "POST", body: JSON.stringify(body) });
}

/** Mark first-run setup finished (System Admin only). */
export function completeSetup(): Promise<SetupStatus> {
  return apiFetch<SetupStatus>("/setup/complete", { method: "POST" });
}
