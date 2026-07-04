/*
 * Undo-not-confirm: the reusable primitive behind "instant action + Undo" that replaces an
 * "Are you sure?" dialog for a reversible operation.
 *
 * The page applies its optimistic state first (flip the row), then hands the real call to this
 * hook. The action runs immediately — it feels instant — and a success toast carries an Undo
 * button for `windowMs`. Clicking Undo fires the inverse call, reverts the optimistic state via
 * `onUndone`, and confirms with a quiet toast. Letting the toast time out (or dismissing it) means
 * the action simply stands.
 *
 * `onUndone` is the single "restore the pre-action state" path — it runs both on an Undo click and
 * when `perform` itself fails, so the page's revert logic is written once. Failures of the inverse
 * call surface the standard blame-free error toast; the list reconciles on its next load.
 *
 * Only one undo window is open at a time: a second undoable action collapses the previous toast
 * (its window ends, its action stands) — no queue.
 */
import { useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";

import { useToast } from "../app/ToastContext";

export interface UndoableOptions<T> {
  /** The real call. The page has already applied its optimistic state before this runs. */
  perform: () => Promise<T>;
  /** The inverse call, given `perform`'s result. */
  undo: (result: T) => Promise<void>;
  /** Toast copy for the success + Undo affordance, already translated. */
  message: string;
  /** Undo button label; defaults to `t("common.undo")`. */
  undoLabel?: string;
  /** How long the Undo affordance stays open, in ms. Defaults to 5000. */
  windowMs?: number;
  /** Restore the page's pre-action state. Runs on an Undo click and on a `perform` failure. */
  onUndone?: () => void;
}

const DEFAULT_WINDOW_MS = 5000;

export type RunUndoable = <T>(opts: UndoableOptions<T>) => Promise<void>;

/** Returns a stable `run(opts)` that performs an action with an Undo window. */
export function useUndoableAction(): RunUndoable {
  const toast = useToast();
  const { t } = useTranslation();
  // The currently-open undo toast, so a second undoable action collapses the first (no queue).
  const openToastId = useRef<number | null>(null);

  return useCallback<RunUndoable>(
    async (opts) => {
      const { perform, undo, message, undoLabel, windowMs = DEFAULT_WINDOW_MS, onUndone } = opts;

      // A new undoable action ends the previous window immediately — that earlier action stands.
      if (openToastId.current !== null) {
        toast.dismiss(openToastId.current);
        openToastId.current = null;
      }

      let result: Awaited<ReturnType<typeof perform>>;
      try {
        result = await perform();
      } catch (error) {
        onUndone?.(); // roll back the optimistic apply
        toast.show(error instanceof Error ? error.message : String(error), "error");
        return;
      }

      let handled = false;
      const id = toast.show(message, "success", {
        duration: windowMs,
        action: {
          label: undoLabel ?? t("common.undo"),
          onClick: () => {
            if (handled) return;
            handled = true;
            openToastId.current = null;
            void (async () => {
              try {
                await undo(result);
                onUndone?.();
                toast.show(t("common.undone"), "info");
              } catch (error) {
                toast.show(error instanceof Error ? error.message : String(error), "error");
              }
            })();
          },
        },
      });
      openToastId.current = id;

      // When the window closes with no Undo, the action stands — just drop our handle to the toast.
      window.setTimeout(() => {
        if (openToastId.current === id) openToastId.current = null;
      }, windowMs);
    },
    [toast, t],
  );
}
