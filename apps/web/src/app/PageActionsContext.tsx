import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { filterMenuItems, type DocMenuItem } from "../components/DocumentMenu";
import { useAuth } from "../auth/AuthContext";
import { usePaletteActions } from "./PaletteActionsContext";

/**
 * Publishes the current page's ONE primary action and its ⋯ overflow items into the sticky
 * PageHeaderBar. Mirrors DocumentCrumb: the provider is remounted per-route in AppShell, so the
 * value resets on every navigation and a page re-publishes it on mount. Rollout to pages is
 * FILE_02/03 — this file just builds the context the bar reads.
 */
export interface PageActions {
  /** The page's single visible primary action (a rendered button). */
  primary?: ReactNode;
  /** Items for the ⋯ menu (print / export / share / doc verbs). `useSetPageActions` permission-filters these. */
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
 *
 * Two things happen centrally here so no page has to do them itself: the ⋯ items are dropped to
 * the ones the signed-in user's role permits (FILE_00 decision 4 — quiet, not greyed), and the
 * surviving items are mirrored into the ⌘K palette's "This page" group (unified-ui FILE_04) so
 * "طباعة"/"تصدير…" are keyboard-reachable, not just mouse-reachable. A page with its own lifecycle
 * palette actions (approve/confirm…) registers those separately via `usePaletteActions`; this is
 * an additional, independently-keyed slot, so the two never collide.
 */
export function useSetPageActions(actions: PageActions): void {
  const setActions = useContext(PageActionsContext)?.setActions;
  const { primary, menuItems } = actions;
  const { hasRole } = useAuth();

  const allowedMenuItems = useMemo(
    () => (menuItems ? filterMenuItems(menuItems, hasRole) : menuItems),
    [menuItems, hasRole],
  );

  useEffect(() => {
    setActions?.({ primary, menuItems: allowedMenuItems });
    return () => setActions?.({});
  }, [setActions, primary, allowedMenuItems]);

  const paletteItems = useMemo(
    () =>
      (allowedMenuItems ?? [])
        .filter((item) => !item.disabled)
        .map((item) => ({ id: item.key, label: item.label, run: item.onClick })),
    [allowedMenuItems],
  );
  usePaletteActions("page-bar-menu", paletteItems);
}
