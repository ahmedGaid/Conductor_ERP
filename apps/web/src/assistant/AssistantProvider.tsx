import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { assistantStatus } from "../api/assistant";

/**
 * Shared state for the global AI panel — mounted once in the app shell so the command-bar button,
 * the ⌘J shortcut and the panel itself all drive one instance. Open state, layout mode and the
 * last conversation persist in localStorage, so reopening the app puts you exactly where you left
 * off. `enabled` comes from /assistant/status once: while it's unknown every AI surface renders
 * nothing (no flicker), and when the provider key is absent the whole feature stays hidden.
 *
 * The full page at /assistant is a route, not a panel mode — the panel's expand button navigates
 * there. So the panel toggles between just two layouts.
 */
export type AssistantMode = "floating" | "docked";

interface AssistantState {
  open: boolean;
  mode: AssistantMode;
  conversationId: number | null;
  enabled: boolean;
  openPanel(): void;
  closePanel(): void;
  toggle(): void;
  setMode(m: AssistantMode): void;
  setConversationId(id: number | null): void;
}

const KEY_OPEN = "assistant.open";
const KEY_MODE = "assistant.mode";
const KEY_CONVERSATION = "assistant.lastConversation";

function readMode(): AssistantMode {
  return localStorage.getItem(KEY_MODE) === "docked" ? "docked" : "floating";
}

function readConversation(): number | null {
  const raw = localStorage.getItem(KEY_CONVERSATION);
  const n = raw ? Number(raw) : NaN;
  return Number.isFinite(n) ? n : null;
}

const AssistantContext = createContext<AssistantState | null>(null);

export function AssistantProvider({ children }: { children: ReactNode }) {
  // null = not yet known; keeps every surface hidden until /status answers.
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [open, setOpen] = useState<boolean>(() => localStorage.getItem(KEY_OPEN) === "1");
  const [mode, setModeState] = useState<AssistantMode>(readMode);
  const [conversationId, setConversationState] = useState<number | null>(readConversation);

  useEffect(() => {
    let alive = true;
    assistantStatus()
      .then((s) => alive && setEnabled(s.enabled))
      .catch(() => alive && setEnabled(false));
    return () => {
      alive = false;
    };
  }, []);

  // Persist so a reload restores the same workspace.
  useEffect(() => localStorage.setItem(KEY_OPEN, open ? "1" : "0"), [open]);
  useEffect(() => localStorage.setItem(KEY_MODE, mode), [mode]);
  useEffect(() => {
    if (conversationId == null) localStorage.removeItem(KEY_CONVERSATION);
    else localStorage.setItem(KEY_CONVERSATION, String(conversationId));
  }, [conversationId]);

  const openPanel = useCallback(() => setOpen(true), []);
  const closePanel = useCallback(() => setOpen(false), []);
  const toggle = useCallback(() => setOpen((v) => !v), []);
  const setMode = useCallback((m: AssistantMode) => setModeState(m), []);
  const setConversationId = useCallback((id: number | null) => setConversationState(id), []);

  const value = useMemo<AssistantState>(
    () => ({
      // Never report "open" while the feature is off/unknown, so no surface flashes on boot.
      open: enabled === true && open,
      mode,
      conversationId,
      enabled: enabled === true,
      openPanel,
      closePanel,
      toggle,
      setMode,
      setConversationId,
    }),
    [enabled, open, mode, conversationId, openPanel, closePanel, toggle, setMode, setConversationId],
  );

  return <AssistantContext.Provider value={value}>{children}</AssistantContext.Provider>;
}

export function useAssistant(): AssistantState {
  const ctx = useContext(AssistantContext);
  if (!ctx) throw new Error("useAssistant must be used within AssistantProvider");
  return ctx;
}
