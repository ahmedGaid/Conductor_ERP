/*
 * Recently-visited destinations for the ⌘K palette. A tiny localStorage-backed MRU list, so
 * opening the palette with an empty query surfaces where you've just been — the fast "jump back"
 * Linear gives you. Each entry is a route path plus an optional label: module/list pages resolve
 * their label from the static command list, while specific entities (an order, an opportunity)
 * register their own human label via `useRecentEntity` once their data has loaded. Best-effort:
 * any storage failure (private mode, quota) degrades silently to "no recents" and never throws
 * into the render path.
 */
const KEY = "conductor:recent-paths";
const MAX = 8;

export interface Recent {
  path: string;
  /** Human label for an entity page (e.g. an order number). Absent for plain module/list pages. */
  label?: string;
}

export function getRecents(): Recent[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    // Tolerate the older string[] shape so an upgrade doesn't wipe a user's history.
    return parsed
      .map((e): Recent | null =>
        typeof e === "string"
          ? { path: e }
          : e && typeof e === "object" && typeof (e as Recent).path === "string"
            ? { path: (e as Recent).path, label: (e as Recent).label }
            : null,
      )
      .filter((e): e is Recent => e !== null);
  } catch {
    return [];
  }
}

/**
 * Record a visit. Moves the path to the front (most-recent-first), capping the list. A `label`
 * upgrades the entry (an entity page reporting its title); omitting it keeps any label already
 * stored, so the plain route-change recorder never clobbers a richer label.
 */
export function recordRecent(path: string, label?: string): void {
  if (!path) return;
  try {
    const existing = getRecents();
    const prior = existing.find((e) => e.path === path);
    const entry: Recent = { path, label: label ?? prior?.label };
    const next = [entry, ...existing.filter((e) => e.path !== path)].slice(0, MAX);
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable — recents are a convenience, never required */
  }
}
