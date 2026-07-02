// Cross-module helpers. resolveEntity turns a business key (an order/journal number) into the
// record's UUID, so universal entity links can route to a UUID-keyed detail page without the id.
import { apiFetch } from "./client";

export function resolveEntity(type: string, key: string): Promise<{ id: string }> {
  return apiFetch<{ id: string }>(
    `/core/resolve?type=${encodeURIComponent(type)}&key=${encodeURIComponent(key)}`,
  );
}

// One live hit from the universal search backing the ⌘K palette (Charter R10). `type` is a stable
// key the UI localizes; `to` is a ready client route; `label`/`sublabel` are pre-shaped for display.
export interface SearchHit {
  type: "customer" | "supplier" | "item" | "sales_order" | "purchase_order" | "journal";
  label: string;
  sublabel: string;
  to: string;
}

// Search customers, suppliers, items, orders and journals by name or number — Arabic-tolerant,
// permission-scoped server-side. Returns [] for queries shorter than the server's minimum.
export function searchEntities(q: string): Promise<SearchHit[]> {
  return apiFetch<SearchHit[]>(`/core/search?q=${encodeURIComponent(q)}`);
}
