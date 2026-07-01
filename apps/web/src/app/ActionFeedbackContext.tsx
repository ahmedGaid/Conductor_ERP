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

/*
 * Action feedback — the app's rich, contextual answer to "what just happened?".
 *
 * Where a Toast is a one-line acknowledgement, an ActionReceipt is the full aftermath of a
 * consequential transaction: the result, what it means for the business, the recommended next
 * step, quick actions to keep working, links to the records it touched, the numbers that matter,
 * any warnings, and a deterministic insight. It never blocks — it appears, invites, and fades.
 *
 * One receipt is live at a time (a new action supersedes the last); it auto-dismisses unless the
 * user hovers it. The surface it renders in (floating / banner) is chosen elsewhere — this context
 * owns only the model and its lifecycle, not the pixels.
 *
 * Mounted once in the app shell (beside the Toaster); reach it from any page via
 * `useActionFeedback()`.
 */

export type FeedbackVariant = "success" | "error" | "info";

/** A single labelled number/value shown in the facts grid (e.g. Amount · EGP 12,540). */
export interface ReceiptFact {
  label: string;
  value: string;
}

/** An action the user can take straight from the receipt. `run` closes the receipt. */
export interface ReceiptAction {
  label: string;
  /** Icon name from `app/icons.tsx` (optional; the recommended action usually carries one). */
  icon?: string;
  run: () => void;
}

/** A one-click link to a related record. Rendered as a router link (with hover-prefetch upstream). */
export interface ReceiptLink {
  label: string;
  to: string;
}

export interface ActionReceipt {
  variant: FeedbackVariant;
  /** The result, in plain words: "Sales order SO-10452 created". */
  title: string;
  /** What it means for the business: "This order is ready to confirm." */
  context?: string;
  /** The single most-likely next step, rendered as the accented primary. */
  next?: ReceiptAction;
  /**
   * Records this action produced — the numbers worth a one-click open (invoice, credit note, GL
   * entry…). Shown in BOTH the simple and rich modes; the heart of the simple receipt.
   */
  documents?: ReceiptLink[];
  /**
   * The way out of a blocker — one-click links that clear what stopped the action (e.g. "Receive
   * ITEM-3" when a delivery is short on stock). Shown in BOTH modes on error receipts.
   */
  resolutions?: ReceiptLink[];
  /** Further actions to keep working without leaving the flow. Rich mode only. */
  quickActions?: ReceiptAction[];
  /** Links to related records (customer, lists) — navigation, not produced docs. Rich mode only. */
  related?: ReceiptLink[];
  /** The numbers worth surfacing (amount, item count, status…). */
  facts?: ReceiptFact[];
  /** Non-blocking cautions ("Credit used 78%"). Surfaced, never gating. */
  warnings?: string[];
  /** Deterministic, data-derived observations ("All items in stock; can fulfil now"). Rich mode only. */
  insights?: string[];
  /** Auto-dismiss delay in ms. `0` keeps it until dismissed. Defaults per variant. */
  duration?: number;
}

interface LiveReceipt extends ActionReceipt {
  id: number;
}

export interface ActionFeedbackApi {
  /** Show a receipt (replacing any live one). Returns its id for later `update`. */
  show: (receipt: ActionReceipt) => number;
  /** Merge late-arriving fields (e.g. an async insight) into a live receipt. No-op if superseded. */
  update: (id: number, patch: Partial<ActionReceipt>) => void;
  dismiss: (id: number) => void;
}

interface FeedbackState extends ActionFeedbackApi {
  receipt: LiveReceipt | null;
  /** Hover pauses the auto-dismiss; leaving resumes it. */
  pause: () => void;
  resume: () => void;
}

const FeedbackContext = createContext<FeedbackState | null>(null);

// Errors linger (something needs the user's attention); successes clear on their own but stay long
// enough to read the next step and reach for a quick action.
const DURATION: Record<FeedbackVariant, number> = { success: 9000, info: 9000, error: 0 };

export function ActionFeedbackProvider({ children }: { children: ReactNode }) {
  const [receipt, setReceipt] = useState<LiveReceipt | null>(null);
  const seq = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // The live receipt's own duration, kept for resume after a hover pause.
  const activeDuration = useRef(0);

  const clearTimer = useCallback(() => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);

  const dismiss = useCallback(
    (id: number) => {
      setReceipt((cur) => (cur && cur.id === id ? null : cur));
      clearTimer();
    },
    [clearTimer],
  );

  const arm = useCallback(
    (id: number, duration: number) => {
      clearTimer();
      if (duration > 0) timer.current = setTimeout(() => dismiss(id), duration);
    },
    [clearTimer, dismiss],
  );

  const show = useCallback<ActionFeedbackApi["show"]>(
    (next) => {
      const id = ++seq.current;
      const duration = next.duration ?? DURATION[next.variant];
      activeDuration.current = duration;
      setReceipt({ ...next, id });
      arm(id, duration);
      return id;
    },
    [arm],
  );

  const update = useCallback<ActionFeedbackApi["update"]>((id, patch) => {
    setReceipt((cur) => (cur && cur.id === id ? { ...cur, ...patch, id } : cur));
  }, []);

  const pause = useCallback(() => clearTimer(), [clearTimer]);
  const resume = useCallback(() => {
    setReceipt((cur) => {
      if (cur) arm(cur.id, activeDuration.current);
      return cur;
    });
  }, [arm]);

  // Never fire a dismiss into a torn-down tree.
  useEffect(() => () => clearTimer(), [clearTimer]);

  const value = useMemo<FeedbackState>(
    () => ({ receipt, show, update, dismiss, pause, resume }),
    [receipt, show, update, dismiss, pause, resume],
  );
  return <FeedbackContext.Provider value={value}>{children}</FeedbackContext.Provider>;
}

/** Page-facing API: fire, enrich, and dismiss action receipts. */
export function useActionFeedback(): ActionFeedbackApi {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error("useActionFeedback must be used within ActionFeedbackProvider");
  const { show, update, dismiss } = ctx;
  return useMemo(() => ({ show, update, dismiss }), [show, update, dismiss]);
}

/** Internal: the host reads the live receipt to render it. */
export function useActionFeedbackState(): FeedbackState {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error("useActionFeedbackState must be used within ActionFeedbackProvider");
  return ctx;
}
