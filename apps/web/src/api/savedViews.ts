// Saved views — a user's named filter presets for one list page. Each stores the list's URL query
// string (the same scheme <FilterBar> deep-links through); applying a view is just navigating to it.
// All endpoints are owner-scoped server-side: a user only ever sees and touches their own.

import { apiFetch } from "./client";

export interface SavedView {
  id: number;
  list_key: string;
  name: string;
  /** The list's URL query string, e.g. "status=confirmed&customer=Acme". Blank = the whole list. */
  query: string;
  is_default: boolean;
}

export function listSavedViews(listKey: string): Promise<SavedView[]> {
  return apiFetch<SavedView[]>(`/identity/saved-views?list_key=${encodeURIComponent(listKey)}`);
}

export function createSavedView(input: {
  list_key: string;
  name: string;
  query: string;
  is_default?: boolean;
}): Promise<SavedView> {
  return apiFetch<SavedView>("/identity/saved-views", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function renameSavedView(id: number, name: string): Promise<SavedView> {
  return apiFetch<SavedView>(`/identity/saved-views/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export function deleteSavedView(id: number): Promise<void> {
  return apiFetch<void>(`/identity/saved-views/${id}`, { method: "DELETE" });
}

export function setDefaultSavedView(id: number): Promise<SavedView> {
  return apiFetch<SavedView>(`/identity/saved-views/${id}/default`, { method: "POST" });
}
