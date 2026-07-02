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
 * Closes on Escape, on a click outside, and on scroll/resize (which would otherwise leave it
 * detached from its anchor). Direction-aware: the panel's inline-start edge lines up with the
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
      onClose();
    }
    const onReflow = () => onClose();
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer, true);
    window.addEventListener("resize", onReflow);
    // Capture scroll anywhere (incl. inner scroll areas) so the panel never floats away.
    window.addEventListener("scroll", onReflow, true);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer, true);
      window.removeEventListener("resize", onReflow);
      window.removeEventListener("scroll", onReflow, true);
    };
  }, [open, onClose, anchorRef]);

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
