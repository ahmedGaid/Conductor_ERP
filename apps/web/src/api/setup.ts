import { apiFetch } from "./client";

export interface SetupStatus {
  is_setup_complete: boolean;
}

/** Whether first-run setup is done — the post-login route guard reads this. */
export function getSetupStatus(): Promise<SetupStatus> {
  return apiFetch<SetupStatus>("/setup/status");
}

/** Mark first-run setup finished (System Admin only). */
export function completeSetup(): Promise<SetupStatus> {
  return apiFetch<SetupStatus>("/setup/complete", { method: "POST" });
}
