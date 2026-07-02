/*
 * Last-used picks for low-friction document creation. A new quotation/order pre-fills the
 * customer / warehouse / tax code the user chose last time, so repeat work isn't re-keyed —
 * the smart-default half of the daily money loop. One value per key, localStorage-backed,
 * best-effort: any storage failure (private mode, quota) degrades silently to "no memory"
 * and never throws into the render path.
 */
const PREFIX = "conductor:last-used:";

export function getLastUsed(key: string): string | null {
  try {
    return localStorage.getItem(PREFIX + key);
  } catch {
    return null;
  }
}

export function setLastUsed(key: string, value: string): void {
  if (!value) return;
  try {
    localStorage.setItem(PREFIX + key, value);
  } catch {
    /* storage unavailable — last-used is a convenience, never required */
  }
}
