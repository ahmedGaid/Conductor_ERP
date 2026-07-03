import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

/**
 * A page-scoped action surfaced at the top of the ⌘K palette ("This page"). Unlike the static
 * go-to/create commands, these are contextual — the order detail page contributes "Approve" /
 * "Confirm", a list page could contribute "New …". Each runs a callback rather than navigating.
 */
export interface PaletteAction {
  id: string;
  label: string;
  run: () => void;
}

interface PaletteActionsValue {
  actions: PaletteAction[];
  setActions: (key: string, actions: PaletteAction[]) => void;
  clearActions: (key: string) => void;
}

const PaletteActionsContext = createContext<PaletteActionsValue | null>(null);

/**
 * Holds the contextual actions the current page has registered. Keyed by a caller-stable id so a
 * page replacing its actions (or unmounting) cleanly supersedes its own previous set without
 * touching anyone else's. Lives above both the palette (in the command bar) and the routed pages.
 */
export function PaletteActionsProvider({ children }: { children: ReactNode }) {
  const [registry, setRegistry] = useState<Record<string, PaletteAction[]>>({});

  const setActions = useCallback((key: string, actions: PaletteAction[]) => {
    setRegistry((r) => ({ ...r, [key]: actions }));
  }, []);

  const clearActions = useCallback((key: string) => {
    setRegistry((r) => {
      if (!(key in r)) return r;
      const next = { ...r };
      delete next[key];
      return next;
    });
  }, []);

  // Flatten in a stable order; pages register one key each, so this is a short list.
  const actions = useMemo(() => Object.values(registry).flat(), [registry]);

  const value = useMemo(
    () => ({ actions, setActions, clearActions }),
    [actions, setActions, clearActions],
  );

  return <PaletteActionsContext.Provider value={value}>{children}</PaletteActionsContext.Provider>;
}

/** Read the registered page actions (used by the palette). Safe outside a provider → empty. */
export function usePaletteActionList(): PaletteAction[] {
  return useContext(PaletteActionsContext)?.actions ?? [];
}

/**
 * Register a page's contextual palette actions for as long as the calling component is mounted.
 * Pass a stable `key` (e.g. "order-detail") and the current actions; they're re-published whenever
 * they change and withdrawn on unmount. Re-reads the latest actions each run, so callers don't need
 * to memoise — only the `key` identifies the slot. No-op outside a provider.
 */
export function usePaletteActions(key: string, actions: PaletteAction[]): void {
  const ctx = useContext(PaletteActionsContext);
  // Pull out the *stable* setters (useCallback []) — depending on the whole ctx value would re-fire
  // this effect on every registry change (the value is rebuilt each time), turning the register +
  // cleanup into a ping-pong that strands stale actions. With stable setters the effect runs only
  // when the page or its action set actually changes.
  const setActions = ctx?.setActions;
  const clearActions = ctx?.clearActions;
  // Serialise the action identities/labels so we only re-publish on a real change, not every render.
  const signature = actions.map((a) => `${a.id}:${a.label}`).join("|");
  const actionsRef = useRef(actions);
  actionsRef.current = actions;

  useEffect(() => {
    if (!setActions || !clearActions) return;
    setActions(key, actionsRef.current);
    return () => clearActions(key);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setActions, clearActions, key, signature]);
}

export { PaletteActionsContext };
