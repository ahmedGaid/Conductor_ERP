// What the assistant already knows without asking. Collected fresh per message send — synchronous,
// no API calls, so it can be gathered inline right before a chat/ask request goes out.
import i18n from "../i18n";
import { moduleFromPath } from "../app/AppShell";
import { getDocumentCrumb } from "../app/DocumentCrumb";

export interface PageContext {
  path: string; // location.hash route, e.g. "/sales/orders/42"
  module: string | null; // sales | purchasing | inventory | accounting | crm | null
  record: { type: string; id: string; label: string } | null; // from DocumentCrumb
  language: "ar" | "en";
  recent: string[]; // last 5 visited module paths
  filters: Record<string, string>; // current route's query params, capped
  dirty: boolean; // true when the current page has unsaved form changes
  // true when the user detached the page record from this conversation (context chip ×):
  // the record still travels as background, but the server stops treating it as the subject.
  detached?: boolean;
}

const RECENT_KEY = "assistant.recentPages";
const RECENT_MAX = 5;
const FILTERS_MAX = 10;
const FILTER_VALUE_MAX = 80;

// A tiny module-level flag a form sets while it has unsaved changes; read fresh on every send.
let dirtyFlag = false;
export function markFormDirty(v: boolean): void {
  dirtyFlag = v;
}

function currentFilters(): Record<string, string> {
  const params = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  const filters: Record<string, string> = {};
  for (const [key, value] of params) {
    if (Object.keys(filters).length >= FILTERS_MAX) break;
    filters[key] = value.slice(0, FILTER_VALUE_MAX);
  }
  return filters;
}

/** Called from AppShell on every navigation to a module page; ignored elsewhere. */
export function pushRecentPage(path: string, module: string | undefined): void {
  if (!module) return;
  try {
    const list = recentPages().filter((p) => p !== path);
    sessionStorage.setItem(RECENT_KEY, JSON.stringify([path, ...list].slice(0, RECENT_MAX)));
  } catch {
    /* sessionStorage unavailable (private mode) — recent pages just stay empty */
  }
}

function recentPages(): string[] {
  try {
    const raw = sessionStorage.getItem(RECENT_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function currentRecord(path: string): PageContext["record"] {
  const label = getDocumentCrumb();
  if (!label) return null;
  const [, seg1 = "", seg2 = "", seg3 = ""] = path.split("/");
  if (!seg2 || !seg3) return null;
  return { type: `${seg1}.${seg2}`, id: seg3, label };
}

export function collectContext(opts?: { detached?: boolean }): PageContext {
  const path = window.location.hash.slice(1) || "/";
  return {
    path,
    module: moduleFromPath(path) ?? null,
    record: currentRecord(path),
    language: (i18n.resolvedLanguage || i18n.language || "ar").startsWith("ar") ? "ar" : "en",
    recent: recentPages(),
    filters: currentFilters(),
    dirty: dirtyFlag,
    ...(opts?.detached ? { detached: true } : {}),
  };
}
