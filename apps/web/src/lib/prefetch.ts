/*
 * Hover/focus prefetch for `useAsync` cache keys.
 *
 * Call on a link's pointer-enter/focus to warm the destination's data *before*
 * the user arrives: the loader runs in the background and seeds the same cache
 * key the target page reads, so the next view paints from cache instead of
 * cold-loading. A no-op when the key is already cached, and errors are swallowed
 * — a speculative prefetch must never surface a failure to the user.
 */
import { readCache, writeCache } from "./cache";

export function prefetch<T>(key: string, loader: () => Promise<T>): void {
  if (readCache(key) !== undefined) return;
  loader()
    .then((value) => writeCache(key, value))
    .catch(() => {
      /* speculative — ignore; the real load on navigation will report any error */
    });
}
