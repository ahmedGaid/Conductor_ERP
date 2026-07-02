import { useSyncExternalStore } from "react";

/*
 * How much an ActionReceipt shows — a client-only preference (Settings → Appearance). Both modes
 * float in the block-end / inline-end corner; they differ only in depth:
 *
 *  - "simple" (default): the result, the number/link of any record it produced, and the one
 *    recommended next step. Nothing else. The calm default.
 *  - "rich": the full after-action panel — facts, warnings, deterministic insights, quick actions,
 *    and related links.
 *
 * Kept in localStorage (no server round-trip) and broadcast so the live host re-renders the moment
 * it changes, in this tab or another.
 */
export type FeedbackMode = "simple" | "rich";

export const FEEDBACK_MODES: FeedbackMode[] = ["simple", "rich"];

const KEY = "conductor:feedback-mode";
const DEFAULT: FeedbackMode = "simple";
// Same-tab writes don't fire the native `storage` event, so we broadcast our own.
const EVENT = "conductor:feedback-mode-change";

function isMode(v: string | null): v is FeedbackMode {
  return v === "simple" || v === "rich";
}

export function getFeedbackMode(): FeedbackMode {
  try {
    const v = localStorage.getItem(KEY);
    return isMode(v) ? v : DEFAULT;
  } catch {
    return DEFAULT;
  }
}

export function setFeedbackMode(mode: FeedbackMode): void {
  try {
    localStorage.setItem(KEY, mode);
  } catch {
    /* private-mode / quota — the broadcast below still updates the live host */
  }
  window.dispatchEvent(new CustomEvent(EVENT));
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** Live-reactive read of the chosen mode. */
export function useFeedbackMode(): FeedbackMode {
  return useSyncExternalStore(subscribe, getFeedbackMode, () => DEFAULT);
}
