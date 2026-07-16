// Health/system-check are unauthenticated and don't use the {data}/{error} envelope, so they
// bypass apiFetch and hit the endpoint directly (proxied in dev — see vite.config.ts).
export interface HealthReport {
  ok: boolean;
  version: string;
}

export async function getHealth(): Promise<HealthReport> {
  const res = await fetch("/health");
  if (!res.ok) throw new Error(`Health check failed (${res.status})`);
  return res.json();
}
