import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";

/**
 * Read a `?prefill=` JSON param once and hand the values to a create form's initial state
 * (assistant guided detours, plan session 12: a "create the missing customer" deep link arrives
 * with the extracted name already filled in).
 *
 * Additive by design: only keys the form declares in `allowed` pass through, only string values,
 * and a missing/malformed param yields `{}` so defaults are untouched. The param is stripped from
 * the URL after the first read — a refresh or share of the page doesn't re-prefill.
 */
export function usePrefill(allowed: readonly string[]): Record<string, string> {
  const [params, setParams] = useSearchParams();
  const consumed = useRef<Record<string, string> | null>(null);

  if (consumed.current === null) {
    const values: Record<string, string> = {};
    const raw = params.get("prefill");
    if (raw) {
      try {
        const parsed: unknown = JSON.parse(raw);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          for (const [k, v] of Object.entries(parsed)) {
            if (allowed.includes(k) && typeof v === "string") values[k] = v;
          }
        }
      } catch {
        /* malformed prefill is ignored — the form simply opens blank */
      }
    }
    consumed.current = values;
  }

  // Consume the param: strip it from the URL so reload/back doesn't re-apply stale values.
  useEffect(() => {
    if (params.has("prefill")) {
      const next = new URLSearchParams(params);
      next.delete("prefill");
      setParams(next, { replace: true });
    }
    // run once on mount — the values were already captured above
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return consumed.current;
}
