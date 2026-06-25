/*
 * Recently-visited pages for the ⌘K palette. A tiny localStorage-backed MRU list of route
 * paths, so opening the palette with an empty query surfaces where you've just been — the
 * fast "jump back" Linear gives you. Best-effort: any storage failure (private mode, quota)
 * degrades silently to "no recents" and never throws into the render path.
 */
const KEY = "conductor:recent-paths";
const MAX = 8;

export function getRecents(): string[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter((p): p is string => typeof p === "string") : [];
  } catch {
    return [];
  }
}

export function recordRecent(path: string): void {
  if (!path) return;
  try {
    const next = [path, ...getRecents().filter((p) => p !== path)].slice(0, MAX);
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable — recents are a convenience, never required */
  }
}
