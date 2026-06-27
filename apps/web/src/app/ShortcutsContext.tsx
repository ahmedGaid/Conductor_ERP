import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

/**
 * Shared open/close state for the keyboard-shortcuts cheat-sheet, so it can be opened from several
 * places (the global `?` key and the sidebar's product menu) while a single dialog instance is
 * mounted in the app shell. Mirrors HelpContext.
 */
interface ShortcutsState {
  open: boolean;
  openShortcuts: () => void;
  closeShortcuts: () => void;
}

const ShortcutsContext = createContext<ShortcutsState | null>(null);

export function ShortcutsProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  const value = useMemo<ShortcutsState>(
    () => ({
      open,
      openShortcuts: () => setOpen(true),
      closeShortcuts: () => setOpen(false),
    }),
    [open],
  );

  return <ShortcutsContext.Provider value={value}>{children}</ShortcutsContext.Provider>;
}

export function useShortcuts(): ShortcutsState {
  const ctx = useContext(ShortcutsContext);
  if (!ctx) throw new Error("useShortcuts must be used within ShortcutsProvider");
  return ctx;
}
