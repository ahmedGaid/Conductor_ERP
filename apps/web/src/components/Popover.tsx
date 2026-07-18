import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";

import "./Popover.css";

interface PopoverProps {
  open: boolean;
  onClose: () => void;
  /** The element the panel is anchored beneath. */
  anchorRef: RefObject<HTMLElement | null>;
  children: ReactNode;
  /** Extra class on the panel (e.g. to set a width). */
  className?: string;
  /** Group label for assistive tech. */
  ariaLabel?: string;
}

/**
 * A floating panel anchored beneath a trigger. Portalled to <body> with `position: fixed`, so it is
 * never clipped by an `overflow` ancestor (toolbars, table wrappers) and needs no per-call z-index.
 * Closes on Escape, on a click outside, or when an item is picked. On scroll / resize / mobile
 * keyboard it re-anchors to the trigger rather than closing (a soft keyboard opening fires a
 * resize — closing there would dismiss the panel the instant the keyboard appears).
 * Direction-aware: the panel's inline-start edge lines up with the
 * trigger's inline-start edge, so it opens the natural way in both RTL (default) and LTR.
 */
export function Popover({ open, onClose, anchorRef, children, className, ariaLabel }: PopoverProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [coords, setCoords] = useState<{ left: number; top: number } | null>(null);

  const position = useCallback(() => {
    const anchor = anchorRef.current;
    const panel = panelRef.current;
    if (!anchor || !panel) return;
    const a = anchor.getBoundingClientRect();
    const w = panel.offsetWidth;
    const h = panel.offsetHeight;
    const rtl = getComputedStyle(anchor).direction === "rtl";
    // Align the panel's inline-start edge with the trigger's inline-start edge.
    let left = rtl ? a.right - w : a.left;
    // Clamp into the viewport with an 8px margin.
    left = Math.max(8, Math.min(left, window.innerWidth - w - 8));
    // Open below the trigger, but flip above when the panel would overflow the viewport bottom and
    // there is room above (e.g. a menu anchored to a control at the foot of the sidebar).
    let top = a.bottom + 4;
    if (top + h > window.innerHeight - 8 && a.top - h - 4 >= 8) {
      top = a.top - h - 4;
    }
    // Keep the whole panel inside the viewport so a tall panel (e.g. the date-picker calendar)
    // never runs off the bottom edge with its footer clipped.
    top = Math.max(8, Math.min(top, window.innerHeight - h - 8));
    setCoords({ left, top });
  }, [anchorRef]);

  // Measure + place once the panel is in the DOM, before paint (no flicker).
  useLayoutEffect(() => {
    if (open) position();
  }, [open, position]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    function onPointer(e: PointerEvent) {
      const target = e.target as Node;
      if (panelRef.current?.contains(target) || anchorRef.current?.contains(target)) return;
      // A click inside another popover layered over this one (a ComboBox list opened inside the
      // date picker) is not an "outside" click — both are portalled siblings under <body>.
      if (target instanceof Element && target.closest(".popover")) return;
      onClose();
    }
    // Scrolling *inside* the panel (e.g. a long combobox list) leaves it where it is — only a
    // page scroll re-anchors it to the trigger. Scrolls inside *another* popover layered over this
    // one (a ComboBox list opened inside the date picker) also count as "inside", since both are
    // portalled siblings under <body>.
    const onScroll = (e: Event) => {
      const target = e.target as Node;
      if (panelRef.current?.contains(target)) return;
      if (target instanceof Element && target.closest(".popover")) return;
      position();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer, true);
    // Re-anchor on layout changes instead of closing. On mobile the on-screen keyboard fires a
    // window resize (Android) or shrinks only the visual viewport (iOS) — either would otherwise
    // dismiss the popover and its autofocused search field the moment the keyboard opens.
    window.addEventListener("resize", position);
    window.addEventListener("scroll", onScroll, true);
    const vv = window.visualViewport;
    vv?.addEventListener("resize", position);
    vv?.addEventListener("scroll", position);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer, true);
      window.removeEventListener("resize", position);
      window.removeEventListener("scroll", onScroll, true);
      vv?.removeEventListener("resize", position);
      vv?.removeEventListener("scroll", position);
    };
  }, [open, onClose, anchorRef, position]);

  if (!open) return null;

  return createPortal(
    <div
      ref={panelRef}
      role="dialog"
      aria-label={ariaLabel}
      className={className ? `popover ${className}` : "popover"}
      style={{ left: coords?.left ?? -9999, top: coords?.top ?? -9999 }}
    >
      {children}
    </div>,
    document.body,
  );
}
