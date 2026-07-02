/*
 * Optimistic mutation helper.
 *
 * Paints the predicted result instantly, then runs the request in the background:
 *   1. apply `optimistic(current)` to state + cache  →  the screen updates with no spinner
 *   2. await `request()`
 *   3. on success: reconcile the server's authoritative result via `settle` (defaults to
 *      keeping the optimistic value), then show an optional success toast
 *   4. on failure: roll back to the exact pre-action snapshot and show an error toast
 *
 * `current` is captured up front and used verbatim for rollback, so a failed action leaves
 * the view exactly as it was. Cross-list cache invalidation still happens in `apiFetch`, so
 * other affected views refetch on their next visit — this helper only owns the one view it
 * mutates.
 */
import type { ToastApi } from "../app/ToastContext";

export interface OptimisticConfig<T, R> {
  /** The current value, captured for rollback (typically `data ?? []` from `useAsync`). */
  current: T;
  /** Commit a value to state + cache — pass `mutate` from `useAsync`. */
  mutate: (next: T) => void;
  /** Predicted next value, applied instantly before the request resolves. */
  optimistic: (current: T) => T;
  /** The server call. */
  request: () => Promise<R>;
  /** Merge the server's authoritative result back in. Defaults to keeping the optimistic value. */
  settle?: (predicted: T, result: R) => T;
  toast: ToastApi;
  /** Message shown on success. Omit for a silent success. */
  success?: string;
  /** Build the success message from the server result (e.g. include a created doc number).
   *  Used in place of `success` when it returns a non-empty string. */
  successFrom?: (result: R) => string;
  /** Map a thrown error to a user-facing message. Defaults to the error's own message. */
  errorMessage?: (error: unknown) => string;
  /**
   * Handle the failure yourself (after rollback) — e.g. show a rich error receipt with a way to fix
   * the blocker. When provided, the default error toast is suppressed.
   */
  onError?: (error: unknown) => void;
}

export async function runOptimistic<T, R>(cfg: OptimisticConfig<T, R>): Promise<R | undefined> {
  const { current, mutate, optimistic, request, settle, toast, success, successFrom, errorMessage, onError } = cfg;
  const predicted = optimistic(current);
  mutate(predicted);
  try {
    const result = await request();
    mutate(settle ? settle(predicted, result) : predicted);
    const msg = (successFrom && successFrom(result)) || success;
    if (msg) toast.show(msg, "success");
    return result;
  } catch (error) {
    mutate(current); // roll back to the pre-action snapshot
    if (onError) {
      onError(error); // caller owns the failure (e.g. a rich error receipt) — no default toast
      return undefined;
    }
    const message = errorMessage
      ? errorMessage(error)
      : error instanceof Error
        ? error.message
        : String(error);
    toast.show(message, "error");
    return undefined;
  }
}

let tmpSeq = 0;

export interface OptimisticCreateConfig<T extends { id: string }> {
  /** The current list, captured for rollback (typically `data ?? []` from `useAsync`). */
  current: T[];
  /** Commit the list to state + cache — pass `mutate` from `useAsync`. */
  mutate: (next: T[]) => void;
  /** Build the placeholder row to show instantly; it carries the supplied temporary id. */
  placeholder: (tempId: string) => T;
  /** The create call, returning the persisted entity. */
  request: () => Promise<T>;
  toast: ToastApi;
  /** Message shown on success. Omit for a silent success. */
  success?: string;
}

/**
 * Optimistic list insert: prepend a placeholder row immediately, then swap it for the entity the
 * server returns once the create resolves (or roll the list back + toast on failure). Lets a create
 * form clear and refocus without waiting on the round-trip.
 */
export function optimisticCreate<T extends { id: string }>(cfg: OptimisticCreateConfig<T>): Promise<T | undefined> {
  const tempId = `tmp-${++tmpSeq}`;
  return runOptimistic<T[], T>({
    current: cfg.current,
    mutate: cfg.mutate,
    optimistic: (rows) => [cfg.placeholder(tempId), ...rows],
    request: cfg.request,
    settle: (predicted, created) => predicted.map((r) => (r.id === tempId ? created : r)),
    toast: cfg.toast,
    success: cfg.success,
  });
}
