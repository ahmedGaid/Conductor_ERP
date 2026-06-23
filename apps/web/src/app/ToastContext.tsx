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
 * Toast notifications — the app's non-blocking feedback channel.
 *
 * Optimistic mutations use this to report a background failure ("…reverted") or a quiet
 * success without interrupting the user, and it carries the "instant action + Undo" pattern
 * (an optional `action` button) that replaces "Are you sure?" dialogs. Hand-rolled and tiny
 * to stay dependency-free and token-driven, matching the rest of the design system.
 *
 * Mounted once in the app shell; reach it from any page via `useToast()`.
 */

export type ToastVariant = "success" | "error" | "info";

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface Toast {
  id: number;
  message: string;
  variant: ToastVariant;
  action?: ToastAction;
}

interface ShowOptions {
  /** A single action button (e.g. "Undo"). Dismisses the toast when clicked. */
  action?: ToastAction;
  /** Auto-dismiss delay in ms. `0` keeps it until dismissed. Defaults to 4000. */
  duration?: number;
}

export interface ToastApi {
  show: (message: string, variant?: ToastVariant, opts?: ShowOptions) => number;
  dismiss: (id: number) => void;
}

interface ToastState extends ToastApi {
  toasts: Toast[];
}

const ToastContext = createContext<ToastState | null>(null);

const DEFAULT_DURATION = 4000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const seq = useRef(0);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    setToasts((list) => list.filter((toast) => toast.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const show = useCallback<ToastApi["show"]>(
    (message, variant = "info", opts) => {
      const id = ++seq.current;
      setToasts((list) => [...list, { id, message, variant, action: opts?.action }]);
      const duration = opts?.duration ?? DEFAULT_DURATION;
      if (duration > 0) {
        timers.current.set(
          id,
          setTimeout(() => dismiss(id), duration),
        );
      }
      return id;
    },
    [dismiss],
  );

  // Clear any pending timers on unmount so we never fire into a torn-down tree.
  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((timer) => clearTimeout(timer));
  }, []);

  const value = useMemo<ToastState>(() => ({ toasts, show, dismiss }), [toasts, show, dismiss]);
  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

/** Page-facing API: fire and dismiss toasts. */
export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

/** Internal: the `Toaster` reads the live list to render it. */
export function useToastState(): ToastState {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToastState must be used within ToastProvider");
  return ctx;
}
