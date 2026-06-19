import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

/**
 * Shared open/close state for the contextual Help drawer, so the drawer can be
 * opened from more than one place (its own floating button and the top-bar "?"
 * action) while a single instance of the drawer is mounted in the app shell.
 */
interface HelpState {
  open: boolean;
  openHelp: () => void;
  closeHelp: () => void;
  toggleHelp: () => void;
}

const HelpContext = createContext<HelpState | null>(null);

export function HelpProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  const value = useMemo<HelpState>(
    () => ({
      open,
      openHelp: () => setOpen(true),
      closeHelp: () => setOpen(false),
      toggleHelp: () => setOpen((v) => !v),
    }),
    [open],
  );

  return <HelpContext.Provider value={value}>{children}</HelpContext.Provider>;
}

export function useHelp(): HelpState {
  const ctx = useContext(HelpContext);
  if (!ctx) throw new Error("useHelp must be used within HelpProvider");
  return ctx;
}
