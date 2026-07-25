import { useCallback, useSyncExternalStore } from "react";

// Module-identity preview modes — a temporary evaluation switch so the founder can compare, on the
// real app, how a document detail page signals which module it belongs to:
//   - "mono"   : no module hue (current, on-brand) — identity comes from sidebar/crumb/title/icon.
//   - "accent" : a per-module hue (sales blue / purchasing amber) on the in-page key figure + number
//                rule, paired with the module word.
//   - "tag"    : a small coloured module chip next to the document number; the rest stays monochrome.
// Once a mode is chosen this switch (and the two unused branches) come out.
export type ModuleIdentityMode = "mono" | "accent" | "tag";
export type DocumentModule = "sales" | "purchasing";

const STORAGE_KEY = "conductor:moduleIdentityMode";
const EVENT = "conductor:moduleIdentityMode";
const MODES: readonly ModuleIdentityMode[] = ["mono", "accent", "tag"];

function read(): ModuleIdentityMode {
  if (typeof localStorage === "undefined") return "mono";
  const v = localStorage.getItem(STORAGE_KEY);
  return v && (MODES as readonly string[]).includes(v) ? (v as ModuleIdentityMode) : "mono";
}

function subscribe(onChange: () => void): () => void {
  // `storage` covers other tabs; the custom event covers same-tab switches (storage doesn't fire
  // in the tab that wrote the value).
  window.addEventListener("storage", onChange);
  window.addEventListener(EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(EVENT, onChange);
  };
}

/** Current preview mode + a setter. Every mounted reader re-renders when the mode changes. */
export function useModuleIdentity(): [ModuleIdentityMode, (mode: ModuleIdentityMode) => void] {
  const mode = useSyncExternalStore(subscribe, read, () => "mono" as ModuleIdentityMode);
  const setMode = useCallback((next: ModuleIdentityMode) => {
    localStorage.setItem(STORAGE_KEY, next);
    window.dispatchEvent(new Event(EVENT));
  }, []);
  return [mode, setMode];
}
