import { useEffect, useRef, useState } from "react";
import { isModalOpen, isTypingTarget } from "../lib/keyboard";

/**
 * Linear-style keyboard navigation for a list/table. `j`/ArrowDown and `k`/ArrowUp move a
 * row highlight; `Enter`/`o` opens the active row; `Escape` clears the highlight. Bare keys
 * stand down while typing or while a modal dialog owns the keyboard.
 *
 * Returns the active index (-1 when nothing is highlighted) and a setter. The caller marks
 * the active row with `data-kbd-active` (for the highlight + scroll-into-view) and
 * `aria-selected`; this hook scrolls the active row into view as it changes.
 */
export function useListKeyboardNav<T>({
  items,
  onOpen,
  enabled = true,
}: {
  items: T[];
  onOpen: (item: T) => void;
  enabled?: boolean;
}): { active: number; setActive: (index: number) => void } {
  const [active, setActive] = useState(-1);

  // Keep the latest items/handler without re-subscribing the listener on every render.
  const itemsRef = useRef(items);
  itemsRef.current = items;
  const onOpenRef = useRef(onOpen);
  onOpenRef.current = onOpen;

  // Clamp the highlight when the list shrinks (filter/tab change).
  useEffect(() => {
    if (active >= items.length) setActive(items.length - 1);
  }, [items.length, active]);

  useEffect(() => {
    if (!enabled) return;
    function onKey(e: KeyboardEvent) {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isTypingTarget(e.target)) return;
      if (isModalOpen()) return;

      const count = itemsRef.current.length;
      if (count === 0) return;

      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        setActive((i) => (i < 0 ? 0 : Math.min(i + 1, count - 1)));
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        setActive((i) => (i <= 0 ? 0 : i - 1));
      } else if (e.key === "Enter" || e.key === "o") {
        setActive((i) => {
          const item = itemsRef.current[i];
          if (i >= 0 && item !== undefined) {
            e.preventDefault();
            onOpenRef.current(item);
          }
          return i;
        });
      } else if (e.key === "Escape") {
        // No preventDefault — let Popover/FilterBar Esc handlers still fire.
        setActive(-1);
      }
    }

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled]);

  // Scroll the highlighted row into view as the selection moves.
  useEffect(() => {
    if (active < 0) return;
    const row = document.querySelector<HTMLElement>('[data-kbd-active="true"]');
    row?.scrollIntoView({ block: "nearest" });
  }, [active]);

  return { active, setActive };
}
