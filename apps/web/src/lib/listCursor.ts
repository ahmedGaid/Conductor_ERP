/*
 * Per-list cursor memory, so returning from a detail page lands you back on the row you left
 * (keyboard highlight) at the scroll position you left — the "a place, not a set of pages" feel.
 * Keyed by route path, stored in sessionStorage so it lives for the tab session but never leaks
 * across tabs or survives a fresh start. Best-effort: any storage failure degrades silently to
 * "no memory" and never throws into the render path (mirrors lib/recents.ts).
 */
const KEY = "conductor:list-cursors";
const MAX = 12;

export interface ListCursor {
  /** Stable id of the highlighted row, or null when nothing was highlighted (mouse-only browsing). */
  activeId: string | null;
  /** scrollTop of the list's scroll container, for pixel-faithful restore. */
  scrollTop: number;
}

type CursorMap = Record<string, ListCursor>;

function read(): CursorMap {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" ? (parsed as CursorMap) : {};
  } catch {
    return {};
  }
}

export function getListCursor(key: string): ListCursor | null {
  const cur = read()[key];
  if (!cur || typeof cur !== "object") return null;
  const activeId = typeof cur.activeId === "string" ? cur.activeId : null;
  const scrollTop = typeof cur.scrollTop === "number" ? cur.scrollTop : 0;
  return { activeId, scrollTop };
}

export function saveListCursor(key: string, value: ListCursor): void {
  if (!key) return;
  try {
    const map = read();
    delete map[key]; // re-insert last so the oldest key is first when we prune
    map[key] = value;
    const keys = Object.keys(map);
    const pruned: CursorMap = {};
    for (const k of keys.slice(Math.max(0, keys.length - MAX))) pruned[k] = map[k];
    sessionStorage.setItem(KEY, JSON.stringify(pruned));
  } catch {
    /* storage unavailable — cursor memory is a convenience, never required */
  }
}
