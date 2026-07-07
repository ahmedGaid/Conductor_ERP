import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

/**
 * Publishes the current document's display number (e.g. "SO-2026-000007") so the route breadcrumb can
 * show it as the final segment on a detail page. The provider is mounted per-route in AppShell, so the
 * value resets to null on every navigation and a detail page re-publishes it on mount.
 */
interface CrumbState {
  label: string | null;
  setLabel: (label: string | null) => void;
}

const DocumentCrumbContext = createContext<CrumbState | null>(null);

// Mirrors the published label outside React so non-hook callers (the assistant's synchronous
// `collectContext()`) can read "what record is the user viewing" without a re-render.
let currentLabel: string | null = null;
const crumbListeners = new Set<() => void>();

function publishCrumb(label: string | null): void {
  if (label === currentLabel) return;
  currentLabel = label;
  crumbListeners.forEach((fn) => fn());
}

/** The published document crumb label, read outside a component (no hook, no re-render). */
export function getDocumentCrumb(): string | null {
  return currentLabel;
}

/**
 * Notifies on every crumb publish/clear — pairs with `getDocumentCrumb` as a
 * `useSyncExternalStore` source, so the assistant panel's context chip follows the user across
 * record pages while it stays open.
 */
export function subscribeDocumentCrumb(listener: () => void): () => void {
  crumbListeners.add(listener);
  return () => {
    crumbListeners.delete(listener);
  };
}

export function DocumentCrumbProvider({ children }: { children: ReactNode }) {
  const [label, setLabel] = useState<string | null>(null);
  useEffect(() => {
    publishCrumb(label);
    return () => {
      publishCrumb(null);
    };
  }, [label]);
  // Memoize so the context value (and the consumer effect that reads it) only changes when the label
  // actually changes — otherwise a new object each render would loop the publish effect.
  const value = useMemo(() => ({ label, setLabel }), [label]);
  return <DocumentCrumbContext.Provider value={value}>{children}</DocumentCrumbContext.Provider>;
}

/** The published document crumb label, or null when none (read by RouteBreadcrumb). */
export function useDocumentCrumb(): string | null {
  return useContext(DocumentCrumbContext)?.label ?? null;
}

/** Detail pages call this to publish their document number as the final breadcrumb segment. */
export function useSetDocumentCrumb(label: string | null | undefined): void {
  const setLabel = useContext(DocumentCrumbContext)?.setLabel;
  useEffect(() => {
    setLabel?.(label ?? null);
    return () => setLabel?.(null);
  }, [setLabel, label]);
}
