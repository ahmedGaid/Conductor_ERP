import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { isModalOpen, isTypingTarget } from "../lib/keyboard";

// `g` then a destination key — Linear-style "go to" navigation.
const GO_MAP: Record<string, string> = {
  d: "/",
  s: "/sales",
  p: "/purchasing",
  i: "/inventory",
  a: "/accounting",
  e: "/einvoice",
  c: "/crm",
  n: "/notifications",
  w: "/workflows",
  ",": "/settings",
};

/**
 * App-wide keyboard layer. ⌘K/Ctrl+K opens the palette from anywhere (even mid-type);
 * the rest are bare single-key shortcuts that stand down while typing or while a modal
 * dialog owns the keyboard:
 *   g → leader for "go to {module}"      / or c → command palette
 *   ?                                    → shortcuts cheat-sheet
 */
export function useGlobalShortcuts({
  openPalette,
  openShortcuts,
}: {
  openPalette: () => void;
  openShortcuts: () => void;
}) {
  const navigate = useNavigate();
  const goPending = useRef(false);
  const goTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // ⌘K / Ctrl+K is the one shortcut that works even from inside a field.
      if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        openPalette();
        return;
      }
      // Bare shortcuts: ignore modified chords, typing, and open modals.
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isTypingTarget(e.target)) return;
      if (isModalOpen()) return;

      // Leader sequence: a pending `g` consumes the next key as a destination.
      if (goPending.current) {
        goPending.current = false;
        window.clearTimeout(goTimer.current);
        const to = GO_MAP[e.key.toLowerCase()];
        if (to) {
          e.preventDefault();
          navigate(to);
        }
        return;
      }
      if (e.key === "g") {
        goPending.current = true;
        goTimer.current = window.setTimeout(() => {
          goPending.current = false;
        }, 1200);
        return;
      }

      if (e.key === "?") {
        e.preventDefault();
        openShortcuts();
      } else if (e.key === "/" || e.key === "c") {
        e.preventDefault();
        openPalette();
      }
    }

    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.clearTimeout(goTimer.current);
    };
  }, [navigate, openPalette, openShortcuts]);
}
