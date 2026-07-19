import { apiFetch } from "./client";

export type HealthStatus = "healthy" | "warning" | "critical";

export interface SystemComponentReport {
  status: HealthStatus;
  detail: string;
  latency_ms: number;
}

export interface SystemStorageReport extends SystemComponentReport {
  free_bytes: number | null;
  total_bytes: number | null;
}

export interface SystemWorkersReport {
  status: HealthStatus;
  count: number;
  queue_depth: number | null;
  detail: string;
}

export interface SystemBackupReport {
  configured: boolean;
  last_backup_at: string | null;
  detail: string;
}

export type SystemEnvReport = Record<string, "set" | "unset">;

export interface SystemStatus {
  version: string;
  uptime_seconds: number;
  status: HealthStatus;
  database: SystemComponentReport;
  redis: SystemComponentReport;
  storage: SystemStorageReport;
  workers: SystemWorkersReport;
  backup: SystemBackupReport;
  env: SystemEnvReport;
}

export function getSystemStatus(): Promise<SystemStatus> {
  return apiFetch<SystemStatus>("/system/status/");
}
