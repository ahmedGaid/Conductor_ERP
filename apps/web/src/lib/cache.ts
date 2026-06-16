/*
 * Tiny in-memory stale-while-revalidate cache for `useAsync`.
 *
 * Keyed by a caller-supplied string. On revisit, a page hydrates its last-known
 * data synchronously (instant paint) and refreshes in the background — so
 * navigation never flashes a blank "Loading…" beat for data we've already seen.
 *
 * Intentionally process-local and unbounded-but-tiny: it holds at most one entry
 * per logical list/report, and is wiped on a full page reload (fresh session).
 */
const store = new Map<string, unknown>();

export function readCache<T>(key: string): T | undefined {
  return store.get(key) as T | undefined;
}

export function writeCache<T>(key: string, value: T): void {
  store.set(key, value);
}

/** Drop one key, or the whole cache, after a mutation that invalidates it. */
export function clearCache(key?: string): void {
  if (key === undefined) store.clear();
  else store.delete(key);
}

/*
 * Which cached lists a successful write invalidates, by API path prefix. Keeping this map next to
 * the cache (rather than scattered across the api/* clients) means every mutation — current and
 * future — invalidates the right lists from one place: `apiFetch` calls `invalidateForPath` after
 * any non-GET request that succeeds, so a created/changed record is freshly refetched the next time
 * its list is shown instead of lingering as stale cache. First (most specific) prefix wins.
 */
const INVALIDATION: ReadonlyArray<{ prefix: string; keys: readonly string[] }> = [
  { prefix: "/sales/customers", keys: ["sales:customers"] },
  { prefix: "/sales/quotations", keys: ["sales:quotations", "sales:orders"] }, // convert spawns an order
  { prefix: "/sales/orders", keys: ["sales:orders", "dashboard"] },
  { prefix: "/purchasing/suppliers", keys: ["purchasing:suppliers"] },
  { prefix: "/purchasing/requests", keys: ["purchasing:requests", "purchasing:orders"] }, // convert spawns a PO
  {
    prefix: "/purchasing/orders",
    keys: ["purchasing:orders", "inventory:stock-on-hand", "inventory:movements", "accounting:journals", "dashboard"],
  },
  {
    prefix: "/inventory/movements",
    keys: ["inventory:movements", "inventory:stock-on-hand", "accounting:journals", "dashboard"],
  },
  { prefix: "/inventory/items", keys: ["inventory:items"] },
  { prefix: "/inventory/warehouses", keys: ["inventory:warehouses"] },
  { prefix: "/accounting/accounts", keys: ["accounting:accounts"] },
  { prefix: "/accounting/cost-centers", keys: ["accounting:cost-centers"] },
  { prefix: "/accounting/periods", keys: ["accounting:periods"] },
  { prefix: "/accounting/journals", keys: ["accounting:journals", "dashboard"] },
  // Asset acquire / depreciation / dispose all post to the GL.
  { prefix: "/accounting/assets", keys: ["accounting:assets", "accounting:journals", "dashboard"] },
  { prefix: "/einvoice/invoices", keys: ["einvoice:invoices"] },
  { prefix: "/crm/leads", keys: ["crm:leads"] },
  { prefix: "/crm/opportunities", keys: ["crm:opportunities", "sales:orders", "dashboard"] }, // win spawns an SO
  { prefix: "/crm/tickets", keys: ["crm:tickets"] },
  { prefix: "/workflow/workflows", keys: ["workflows"] },
];

/** Evict the cached lists affected by a successful write to `path` (query string ignored). */
export function invalidateForPath(path: string): void {
  const clean = path.split("?")[0];
  for (const { prefix, keys } of INVALIDATION) {
    if (clean.startsWith(prefix)) {
      keys.forEach((k) => store.delete(k));
      return;
    }
  }
}
