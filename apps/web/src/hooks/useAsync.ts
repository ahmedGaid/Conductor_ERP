import { useCallback, useEffect, useState } from "react";

import { clearCache, readCache, writeCache } from "../lib/cache";

interface AsyncState<T> {
  data: T | null;
  /** True only when there is nothing to show yet (a cold load). Never true over cached data. */
  loading: boolean;
  /** True whenever a fetch is in flight, including a silent background revalidation. */
  validating: boolean;
  error: string | null;
  reload: () => void;
  /**
   * Synchronously replace the current data in state *and* cache. Used for optimistic
   * mutations: paint a predicted value instantly, then reconcile (or roll back) once the
   * request settles. See `runOptimistic` in `lib/optimistic`.
   */
  mutate: (next: T | null) => void;
}

/**
 * Run an async loader on mount (and when `deps` change); expose data/loading/error + reload.
 *
 * Pass a `cacheKey` to opt into stale-while-revalidate: the last result is kept in memory and
 * returned instantly on the next visit, while a fresh fetch runs in the background. With a warm
 * cache `loading` stays false, so the page paints its real content immediately instead of flashing
 * a loading placeholder — only a genuine cold load (no cached data) shows `loading`.
 */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[], cacheKey?: string): AsyncState<T> {
  const initial = cacheKey ? readCache<T>(cacheKey) : undefined;
  const [data, setData] = useState<T | null>(initial ?? null);
  const [validating, setValidating] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(loader, deps);

  useEffect(() => {
    let active = true;
    setValidating(true);
    setError(null);
    run()
      .then((value) => {
        if (!active) return;
        setData(value);
        if (cacheKey) writeCache(cacheKey, value);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (active) setValidating(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, nonce]);

  // Cold load = fetching with nothing to show. With a warm cache `data` is already set, so this
  // stays false and the page renders content right away (background refresh is `validating`).
  const loading = validating && data === null;
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const mutate = useCallback(
    (next: T | null) => {
      setData(next);
      if (cacheKey) {
        if (next === null) clearCache(cacheKey);
        else writeCache(cacheKey, next);
      }
    },
    [cacheKey],
  );
  return { data, loading, validating, error, reload, mutate };
}
