import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import type { DocMenuItem } from "../components/DocumentMenu";

/**
 * Publishes the current page's ONE primary action and its ⋯ overflow items into the sticky
 * PageHeaderBar. Mirrors DocumentCrumb: the provider is remounted per-route in AppShell, so the
 * value resets on every navigation and a page re-publishes it on mount. Rollout to pages is
 * FILE_02/03 — this file just builds the context the bar reads.
 */
export interface PageActions {
  /** The page's single visible primary action (a rendered button). */
  primary?: ReactNode;
  /** Items for the ⋯ menu (print / export / share / doc verbs), permission-filtered by the caller. */
  menuItems?: DocMenuItem[];
}

interface PageActionsState {
  actions: PageActions;
  setActions: (actions: PageActions) => void;
}

const PageActionsContext = createContext<PageActionsState | null>(null);

export function PageActionsProvider({ children }: { children: ReactNode }) {
  const [actions, setActions] = useState<PageActions>({});
  // Memoize so the context value only changes when the published actions change — otherwise a new
  // object each render would loop any consumer effect.
  const value = useMemo(() => ({ actions, setActions }), [actions]);
  return <PageActionsContext.Provider value={value}>{children}</PageActionsContext.Provider>;
}

/** The current page's published actions, read by PageHeaderBar. */
export function usePageActions(): PageActions {
  return useContext(PageActionsContext)?.actions ?? {};
}

/**
 * Pages call this to publish their primary action + ⋯ menu into the page header bar.
 * Pass STABLE references (wrap `primary` and `menuItems` in useMemo) — they are effect deps, so a
 * fresh array/node each render would re-publish in a loop.
 */
export function useSetPageActions(actions: PageActions): void {
  const setActions = useContext(PageActionsContext)?.setActions;
  const { primary, menuItems } = actions;
  useEffect(() => {
    setActions?.({ primary, menuItems });
    return () => setActions?.({});
  }, [setActions, primary, menuItems]);
}
