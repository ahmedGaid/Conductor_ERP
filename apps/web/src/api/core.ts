// Cross-module helpers. resolveEntity turns a business key (an order/journal number) into the
// record's UUID, so universal entity links can route to a UUID-keyed detail page without the id.
import { apiFetch } from "./client";

export function resolveEntity(type: string, key: string): Promise<{ id: string }> {
  return apiFetch<{ id: string }>(
    `/core/resolve?type=${encodeURIComponent(type)}&key=${encodeURIComponent(key)}`,
  );
}
