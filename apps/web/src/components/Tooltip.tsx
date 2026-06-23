import {
  cloneElement,
  Fragment,
  useCallback,
  useId,
  useRef,
  useState,
  type ReactElement,
  type Ref,
} from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";

import "./Tooltip.css";

type Placement = "top" | "bottom" | "inlineEnd";
/** Placement after resolving the logical `inlineEnd` against the trigger's writing direction. */
type Side = "top" | "bottom" | "right" | "left";

interface TooltipProps {
  /** The text shown on hover / focus. Already-translated; pass a t("…") value. */
  label: string;
  /**
   * Where to place the bubble. "top"/"bottom" centre it over the trigger; "inlineEnd" sits it
   * beside the trigger toward the content (right in LTR, left in RTL) — for vertical icon rails.
   * Default "top".
   */
  placement?: Placement;
  /** Hover dwell before showing, in ms. Default 500 (Linear-style, unobtrusive). */
  delay?: number;
  /**
   * Optional keyboard shortcut shown as kbd chips beside the label, e.g. ["G", "S"]
   * renders “G then S”. Lets a control advertise its global shortcut on hover/focus.
   */
  shortcut?: string[];
  /** A single focusable element (button/link). It receives the hover/focus wiring. */
  children: ReactElement;
}

interface Coords {
  left: number;
  top: number;
  side: Side;
}

const GAP = 8;

/** Merge our ref with whatever ref the child element already carries. */
function setRef<T>(ref: Ref<T> | undefined, value: T | null) {
  if (typeof ref === "function") ref(value);
  else if (ref && typeof ref === "object") (ref as { current: T | null }).current = value;
}

/**
 * A calm, on-brand tooltip for icon-only / terse controls. Rendered through a portal with
 * `position: fixed`, so it never gets clipped by an `overflow` ancestor (toolbars, table wraps)
 * and never needs a per-call z-index. Direction-agnostic: the bubble is centred over its trigger,
 * so it reads correctly in RTL (Arabic, default) and LTR alike. The fade honours the motion-scale
 * token and flattens under prefers-reduced-motion via the global guard.
 *
 * Accessibility: the trigger is linked to the bubble with `aria-describedby`, and the tip also
 * appears on keyboard focus — not hover only — so it is reachable without a mouse.
 */
export function Tooltip({ label, placement = "top", delay = 500, shortcut, children }: TooltipProps) {
  const { t } = useTranslation();
  const id = useId();
  const triggerRef = useRef<HTMLElement | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const [coords, setCoords] = useState<Coords | null>(null);

  const show = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    if (placement === "inlineEnd") {
      // Beside the trigger, vertically centred, toward the content edge (RTL-aware).
      const rtl = getComputedStyle(el).direction === "rtl";
      const top = r.top + r.height / 2;
      const left = rtl ? r.left - GAP : r.right + GAP;
      setCoords({ left, top, side: rtl ? "left" : "right" });
      return;
    }
    const left = r.left + r.width / 2;
    const top = placement === "top" ? r.top - GAP : r.bottom + GAP;
    setCoords({ left, top, side: placement });
  }, [placement]);

  const open = useCallback(
    (immediate = false) => {
      window.clearTimeout(timer.current);
      if (immediate) show();
      else timer.current = window.setTimeout(show, delay);
    },
    [delay, show],
  );

  const close = useCallback(() => {
    window.clearTimeout(timer.current);
    setCoords(null);
  }, []);

  const childRef = (children as { ref?: Ref<HTMLElement> }).ref;

  const trigger = cloneElement(children as ReactElement<Record<string, unknown>>, {
    ref: (node: HTMLElement | null) => {
      triggerRef.current = node;
      setRef(childRef, node);
    },
    "aria-describedby": coords ? id : undefined,
    onMouseEnter: () => open(),
    onMouseLeave: () => close(),
    onFocus: () => open(true),
    onBlur: () => close(),
  });

  return (
    <>
      {trigger}
      {coords &&
        label &&
        createPortal(
          <span
            id={id}
            role="tooltip"
            className={`tooltip tooltip--${coords.side}${shortcut ? " tooltip--with-keys" : ""}`}
            // Viewport coords for position:fixed are inherently physical; the bubble is then
            // centred over the trigger by a direction-agnostic translate in CSS, so RTL/LTR match.
            style={{ left: coords.left, top: coords.top }}
          >
            <span className="tooltip__label">{label}</span>
            {shortcut && shortcut.length > 0 && (
              <span className="tooltip__keys">
                {shortcut.map((k, i) => (
                  <Fragment key={i}>
                    {i > 0 && <span className="tooltip__then">{t("shortcuts.then")}</span>}
                    <kbd className="tooltip__kbd latin">{k}</kbd>
                  </Fragment>
                ))}
              </span>
            )}
          </span>,
          document.body,
        )}
    </>
  );
}
