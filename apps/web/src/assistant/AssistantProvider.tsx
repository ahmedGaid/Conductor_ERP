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
import { readDetour, writeDetour, type Detour } from "./detour";

// A resume the return-detection surface has requested: run against `conversationId`, replaying the
// paused work on `messageId` with the record the user just created (`resolved`) or null (re-resolve
// by query). ConversationView consumes it once its thread matches and has loaded.
export interface ResumeRequest {
  conversationId: number;
  messageId: number;
  resolved: { entity: string; id: string; label: string } | null;
}

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
  /** Bumps whenever the thread list changes; every ThreadList reloads off it (one source of truth). */
  conversationsNonce: number;
  /** A question handed off from elsewhere (e.g. the ⌘K fallthrough row) awaiting first send. */
  pendingMessage: string | null;
  /** True while the user has detached the page record from this conversation (context chip ×). */
  contextDetached: boolean;
  setContextDetached(v: boolean): void;
  openPanel(): void;
  closePanel(): void;
  toggle(): void;
  setMode(m: AssistantMode): void;
  setConversationId(id: number | null): void;
  refreshConversations(): void;
  /** Opens the panel and queues `text` to be sent as the next message. */
  openPanelWithMessage(text: string): void;
  /** Consumes the pending message so it isn't resent on the next render. */
  clearPendingMessage(): void;
  /** The active guided detour (a suggestion sent the user off to create a record), or null. */
  detour: Detour | null;
  /** Remember an errand so we can bring the user back and continue (persists across a reload). */
  startDetour(detour: Detour): void;
  /** Forget the active detour (returned, cancelled, or resumed). */
  clearDetour(): void;
  /** A resume the return surface has asked ConversationView to run, or null. */
  pendingResume: ResumeRequest | null;
  /** Ask ConversationView to resume the paused work in a conversation. */
  requestResume(req: ResumeRequest): void;
  /** Consume the resume request so it isn't run twice. */
  clearPendingResume(): void;
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
  const [conversationsNonce, setConversationsNonce] = useState(0);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [contextDetached, setContextDetached] = useState(false);
  const [detour, setDetourState] = useState<Detour | null>(readDetour);
  const [pendingResume, setPendingResume] = useState<ResumeRequest | null>(null);

  // Detach is per-conversation: switching (or starting) a thread re-attaches the page context.
  useEffect(() => setContextDetached(false), [conversationId]);

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
  const refreshConversations = useCallback(() => setConversationsNonce((n) => n + 1), []);
  const openPanelWithMessage = useCallback((text: string) => {
    setPendingMessage(text);
    setOpen(true);
  }, []);
  const clearPendingMessage = useCallback(() => setPendingMessage(null), []);
  const startDetour = useCallback((d: Detour) => {
    writeDetour(d); // persist immediately so a full reload mid-errand still returns the user
    setDetourState(d);
  }, []);
  const clearDetour = useCallback(() => {
    writeDetour(null);
    setDetourState(null);
  }, []);
  const requestResume = useCallback((req: ResumeRequest) => setPendingResume(req), []);
  const clearPendingResume = useCallback(() => setPendingResume(null), []);

  const value = useMemo<AssistantState>(
    () => ({
      // Never report "open" while the feature is off/unknown, so no surface flashes on boot.
      open: enabled === true && open,
      mode,
      conversationId,
      enabled: enabled === true,
      conversationsNonce,
      pendingMessage,
      contextDetached,
      setContextDetached,
      openPanel,
      closePanel,
      toggle,
      setMode,
      setConversationId,
      refreshConversations,
      openPanelWithMessage,
      clearPendingMessage,
      detour,
      startDetour,
      clearDetour,
      pendingResume,
      requestResume,
      clearPendingResume,
    }),
    [
      enabled,
      open,
      mode,
      conversationId,
      conversationsNonce,
      pendingMessage,
      contextDetached,
      openPanel,
      closePanel,
      toggle,
      setMode,
      setConversationId,
      refreshConversations,
      openPanelWithMessage,
      clearPendingMessage,
      detour,
      startDetour,
      clearDetour,
      pendingResume,
      requestResume,
      clearPendingResume,
    ],
  );

  return <AssistantContext.Provider value={value}>{children}</AssistantContext.Provider>;
}

export function useAssistant(): AssistantState {
  const ctx = useContext(AssistantContext);
  if (!ctx) throw new Error("useAssistant must be used within AssistantProvider");
  return ctx;
}
