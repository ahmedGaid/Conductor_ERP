import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { isModalOpen, isTypingTarget } from "../lib/keyboard";

/**
 * Linear-style multi-select for a list/table, the companion to useListKeyboardNav. Tracks a set of
 * selected row ids and powers the BulkActionBar. Selection is keyboard-first:
 *   - `x`            toggle the keyboard-active row (from useListKeyboardNav)
 *   - `Shift`+click  / Shift on the checkbox extends a contiguous range from the last toggle
 *   - `⌘`/`Ctrl`+`A` select every visible row (toggles back to none when all are already picked)
 *   - `Escape`       clear the selection
 *
 * `items` is the currently-visible list (after filters/tabs); header "all"/"some" state and ⌘A are
 * computed against it. Selected ids that scroll out of view via a filter are kept, so the bulk action
 * still applies to them; `selectedItems` resolves ids back to the rows still present in `items`.
 */
export function useRowSelection<T>({
  items,
  getItemId,
  activeIndex,
  enabled = true,
}: {
  items: T[];
  getItemId: (item: T) => string;
  /** The useListKeyboardNav active index, so `x` can toggle the highlighted row. */
  activeIndex?: number;
  enabled?: boolean;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Latest values read by the key listener without re-subscribing every render.
  const itemsRef = useRef(items);
  itemsRef.current = items;
  const getIdRef = useRef(getItemId);
  getIdRef.current = getItemId;
  const activeRef = useRef(activeIndex);
  activeRef.current = activeIndex;
  // Anchor index for Shift range-extend.
  const anchorRef = useRef(-1);

  const ids = useMemo(() => items.map(getItemId), [items, getItemId]);
  const allSelected = ids.length > 0 && ids.every((id) => selected.has(id));
  const someSelected = !allSelected && ids.some((id) => selected.has(id));

  const clear = useCallback(() => setSelected(new Set()), []);

  // Toggle one row. When `shiftKey` and an anchor exists, select the whole range between them.
  const toggle = useCallback(
    (index: number, shiftKey = false) => {
      setSelected((prev) => {
        const next = new Set(prev);
        const list = itemsRef.current;
        const get = getIdRef.current;
        if (shiftKey && anchorRef.current >= 0) {
          const [lo, hi] = [anchorRef.current, index].sort((a, b) => a - b);
          const select = !prev.has(get(list[index]));
          for (let i = lo; i <= hi; i++) {
            const id = get(list[i]);
            if (select) next.add(id);
            else next.delete(id);
          }
        } else {
          const id = get(list[index]);
          if (next.has(id)) next.delete(id);
          else next.add(id);
        }
        anchorRef.current = index;
        return next;
      });
    },
    [],
  );

  const toggleAll = useCallback(() => {
    setSelected((prev) => {
      const everyId = itemsRef.current.map(getIdRef.current);
      const all = everyId.length > 0 && everyId.every((id) => prev.has(id));
      return all ? new Set() : new Set(everyId);
    });
    anchorRef.current = -1;
  }, []);

  // Keyboard layer: x / ⌘A / Esc. Bare keys stand down while typing or while a modal owns focus.
  useEffect(() => {
    if (!enabled) return;
    function onKey(e: KeyboardEvent) {
      if (isTypingTarget(e.target) || isModalOpen()) return;
      if ((e.metaKey || e.ctrlKey) && (e.key === "a" || e.key === "A")) {
        if (itemsRef.current.length === 0) return;
        e.preventDefault();
        toggleAll();
      } else if (!e.metaKey && !e.ctrlKey && !e.altKey && (e.key === "x" || e.key === "X")) {
        const i = activeRef.current;
        if (i != null && i >= 0 && i < itemsRef.current.length) {
          e.preventDefault();
          toggle(i, e.shiftKey);
        }
      } else if (e.key === "Escape") {
        setSelected((prev) => (prev.size > 0 ? new Set() : prev));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled, toggle, toggleAll]);

  const isSelected = useCallback((id: string) => selected.has(id), [selected]);
  const selectedItems = useMemo(
    () => items.filter((it) => selected.has(getItemId(it))),
    [items, selected, getItemId],
  );

  return {
    selected,
    selectedItems,
    count: selected.size,
    isSelected,
    toggle,
    toggleAll,
    clear,
    allSelected,
    someSelected,
  };
}
