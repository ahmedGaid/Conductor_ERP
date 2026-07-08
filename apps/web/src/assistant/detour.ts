// Guided-detour state (plan session 13). When a suggestion card sends the user off to create a
// missing record (supplier, customer, item, warehouse), we remember exactly where we left the
// conversation so we can bring them straight back and continue the paused work — no re-upload, no
// "what were we doing?". One active detour at a time: a guided errand, not a task queue.
export interface Detour {
  conversationId: number;
  messageId: number; // the SuggestionCard whose deep link started the errand
  expect: { entity: string; query: string }; // the record we sent them to create
  returnTo: string; // hash path we left (from collectContext().path)
  startedAt: number; // epoch ms — a detour older than STALE_MS asks instead of auto-resuming
}

// After this long we no longer assume the record on screen is the one we asked for — the pill
// switches to "still creating…?" and waits for the user to say so, rather than resuming blindly.
export const DETOUR_STALE_MS = 30 * 60 * 1000;

export function isStale(detour: Detour, now: number = Date.now()): boolean {
  return now - detour.startedAt > DETOUR_STALE_MS;
}

// Blocker entity → the DocumentCrumb record type its detail page publishes (context.ts builds the
// type as "seg1.seg2" from the path). Copied from the server ENTITY_REGISTRY detail routes
// (erp/assistant/services/suggestions.py) — a wrong entry here just means a missed auto-return, so
// the manual "I'm done" button always remains the safety net.
const ENTITY_RECORD_TYPE: Record<string, string> = {
  customer: "sales.customers",
  supplier: "purchasing.suppliers",
  item: "inventory.items",
  warehouse: "inventory.warehouses",
};

/** True when the record now on screen is the kind of record this detour went to create. */
export function recordMatchesDetour(recordType: string, entity: string): boolean {
  const want = ENTITY_RECORD_TYPE[entity];
  return want != null && recordType === want;
}

const KEY_DETOUR = "assistant.detour";

export function readDetour(): Detour | null {
  try {
    const raw = localStorage.getItem(KEY_DETOUR);
    if (!raw) return null;
    const d = JSON.parse(raw) as Detour;
    // Guard against a malformed/stale-shape blob (older build, hand-edited storage).
    if (typeof d?.conversationId !== "number" || typeof d?.messageId !== "number" || !d?.expect) {
      return null;
    }
    return d;
  } catch {
    return null;
  }
}

export function writeDetour(detour: Detour | null): void {
  try {
    if (detour) localStorage.setItem(KEY_DETOUR, JSON.stringify(detour));
    else localStorage.removeItem(KEY_DETOUR);
  } catch {
    /* localStorage unavailable (private mode) — the detour just won't survive a full reload */
  }
}
