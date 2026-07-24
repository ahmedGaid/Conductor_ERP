// Pure, framework-free decisions behind useDraftRecovery — unit-tested in draftRecovery.test.ts.
// Keeping them here (no React, no fetch, no timers) makes the recovery rules testable in isolation.

/** A form value is "meaningful" (worth saving/offering) when it differs from the empty baseline. */
export function isMeaningfulChange<T>(current: T, baseline: T): boolean {
  return JSON.stringify(current) !== JSON.stringify(baseline);
}

export interface Candidate<T> {
  payload: T;
  clientVersion: number;
}

/**
 * On mount, choose which stored copy to offer for recovery. The higher clientVersion wins: a crash
 * that lands after a localStorage mirror but before the server ack leaves the local copy ahead.
 */
export function reconcile<T>(
  server: Candidate<T> | null,
  local: Candidate<T> | null,
): { source: "server" | "local" | "none"; payload: T | null } {
  if (!server && !local) return { source: "none", payload: null };
  if (server && !local) return { source: "server", payload: server.payload };
  if (local && !server) return { source: "local", payload: local.payload };
  if (local!.clientVersion > server!.clientVersion) return { source: "local", payload: local!.payload };
  return { source: "server", payload: server!.payload };
}

/** True when the stored draft has advanced past what this client last saw — a conflicting write. */
export function hasConflict(expectedVersion: number, storedVersion: number): boolean {
  return expectedVersion < storedVersion;
}
