import { useEffect, useRef, useState } from "react";
import { isModalOpen, isTypingTarget } from "../lib/keyboard";
import { getListCursor, saveListCursor } from "../lib/listCursor";

/**
 * Linear-style keyboard navigation for a list/table. `j`/ArrowDown and `k`/ArrowUp move a
 * row highlight; `Enter`/`o` opens the active row; `Escape` clears the highlight. Bare keys
 * stand down while typing or while a modal dialog owns the keyboard.
 *
 * Returns the active index (-1 when nothing is highlighted) and a setter. The caller marks
 * the active row with `data-kbd-active` (for the highlight + scroll-into-view) and
 * `aria-selected`; this hook scrolls the active row into view as it changes.
 *
 * Pass `persistKey` + `getItemId` to make the list "a place": when you open a row and come
 * back, the highlight and scroll position are restored from sessionStorage (see lib/listCursor).
 */
export function useListKeyboardNav<T>({
  items,
  onOpen,
  enabled = true,
  persistKey,
  getItemId,
}: {
  items: T[];
  onOpen: (item: T) => void;
  enabled?: boolean;
  persistKey?: string;
  getItemId?: (item: T) => string;
}): { active: number; setActive: (index: number) => void } {
  const [active, setActive] = useState(-1);

  // Keep the latest items/handler without re-subscribing the listener on every render.
  const itemsRef = useRef(items);
  itemsRef.current = items;
  const onOpenRef = useRef(onOpen);
  onOpenRef.current = onOpen;

  // Latest active index + id accessor, read by the unmount capture without re-running it.
  const activeRef = useRef(active);
  activeRef.current = active;
  const getItemIdRef = useRef(getItemId);
  getItemIdRef.current = getItemId;

  // When restoring a saved highlight, suppress the one scroll-into-view it would trigger so the
  // explicit scrollTop restore (below) wins and the position is pixel-faithful.
  const suppressScrollRef = useRef(false);

  // Restore the saved cursor once, as soon as the list has data. A highlight is only restored if
  // its row still exists; the scroll position is restored regardless (covers mouse-only browsing).
  const restoredRef = useRef(false);
  useEffect(() => {
    if (restoredRef.current || !persistKey || !getItemId || items.length === 0) return;
    restoredRef.current = true;
    const saved = getListCursor(persistKey);
    if (!saved) return;
    if (saved.activeId != null) {
      const idx = itemsRef.current.findIndex((it) => getItemId(it) === saved.activeId);
      if (idx >= 0) {
        suppressScrollRef.current = true;
        setActive(idx);
      }
    }
    const top = saved.scrollTop;
    requestAnimationFrame(() => {
      const el = document.querySelector<HTMLElement>('[class$="-table-wrap"]');
      if (el) el.scrollTop = top;
    });
  }, [persistKey, getItemId, items.length]);

  // On unmount (e.g. opening a row navigates away), capture the highlighted row id + scroll position.
  useEffect(() => {
    if (!persistKey) return;
    return () => {
      const idx = activeRef.current;
      const item = idx >= 0 ? itemsRef.current[idx] : undefined;
      const get = getItemIdRef.current;
      const el = document.querySelector<HTMLElement>('[class$="-table-wrap"]');
      saveListCursor(persistKey, {
        activeId: item && get ? get(item) : null,
        scrollTop: el ? el.scrollTop : 0,
      });
    };
  }, [persistKey]);

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

  // Scroll the highlighted row into view as the selection moves. Skipped for the one change that
  // comes from restoring a saved cursor, so the explicit scrollTop restore stays pixel-faithful.
  useEffect(() => {
    if (active < 0) return;
    if (suppressScrollRef.current) {
      suppressScrollRef.current = false;
      return;
    }
    const row = document.querySelector<HTMLElement>('[data-kbd-active="true"]');
    row?.scrollIntoView({ block: "nearest" });
  }, [active]);

  return { active, setActive };
}
