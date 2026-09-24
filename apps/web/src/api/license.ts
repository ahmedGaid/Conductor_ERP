import { apiFetch } from "./client";

export type LicenseStatus =
  | "unmanaged"
  | "trial"
  | "trial_ended"
  | "active"
  | "invalid"
  | "company_mismatch";

export interface LicenseState {
  status: LicenseStatus;
  edition: string | null;
  modules: string[];
  max_branches: number | null;
  maintenance_active: boolean;
  maintenance_until: string | null;
  ai_active: boolean;
  ai_until: string | null;
  trial_days_left: number | null;
  invalid_reason: string | null;
  clock_rollback: boolean;
  licensed_company_name: string | null;
  licensed_tax_id: string | null;
}

export function getLicenseState(): Promise<LicenseState> {
  return apiFetch<LicenseState>("/license/");
}

export function installLicense(key: string): Promise<LicenseState> {
  return apiFetch<LicenseState>("/license/", { method: "POST", body: JSON.stringify({ key }) });
}
