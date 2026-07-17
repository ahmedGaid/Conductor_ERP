import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import type { HelpSignals } from "./types";

/**
 * Live page state, published by the page and read by the Help drawer's Live tab.
 *
 * Mirrors PageActionsContext deliberately: the provider is remounted per-route in AppShell, so the
 * value resets on every navigation and a page re-publishes on mount. A page that publishes nothing
 * leaves this empty and its guide's Live tab never appears — existing pages are untouched.
 *
 * The direction of knowledge matters: a page states plain facts about itself ({ subCount: 0 }) and
 * knows nothing about help; the guide owns every judgement about what those facts mean.
 */
interface HelpSignalsState {
  signals: HelpSignals;
  setSignals: (signals: HelpSignals) => void;
}

const HelpSignalsContext = createContext<HelpSignalsState | null>(null);

export function HelpSignalsProvider({ children }: { children: ReactNode }) {
  const [signals, setSignals] = useState<HelpSignals>({});
  // Memoized so the value only changes when the published signals do — a fresh object per render
  // would loop the consumer effect, same hazard PageActionsProvider guards against.
  const value = useMemo(() => ({ signals, setSignals }), [signals]);
  return <HelpSignalsContext.Provider value={value}>{children}</HelpSignalsContext.Provider>;
}

/** The current page's published signals, read by the Help drawer. */
export function useHelpSignals(): HelpSignals {
  return useContext(HelpSignalsContext)?.signals ?? {};
}

/**
 * Pages call this to publish the live facts their guide's Live tab reacts to.
 *
 * Unlike `useSetPageActions`, the argument does NOT need to be a stable reference: signals are
 * primitives, so this serializes them and only re-publishes when a value actually changes. That
 * keeps the call site honest — a page can write the object inline, which is the whole point.
 */
export function useSetHelpSignals(signals: HelpSignals): void {
  const setSignals = useContext(HelpSignalsContext)?.setSignals;
  const key = JSON.stringify(signals);

  useEffect(() => {
    setSignals?.(JSON.parse(key) as HelpSignals);
    return () => setSignals?.({});
  }, [setSignals, key]);
}
