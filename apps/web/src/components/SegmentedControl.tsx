import { useRef, type KeyboardEvent, type ReactNode } from "react";

import "./SegmentedControl.css";

export interface SegmentedOption<T extends string> {
  value: T;
  /** Visible content — text, or text + a count badge (#4 list tabs). */
  label: ReactNode;
  disabled?: boolean;
}

interface SegmentedControlProps<T extends string> {
  value: T;
  options: SegmentedOption<T>[];
  onChange: (value: T) => void;
  /** Group label for assistive tech (the control has no visible <label>). */
  ariaLabel: string;
}

/**
 * A single-choice segmented control: a horizontal radio group rendered as pill buttons. The calm,
 * all-options-visible alternative to a <select> for 2–5 mutually-exclusive choices — the charter's
 * "a segmented control over a dropdown" rule, made one shared component so every surface (settings,
 * list filters, view toggles) reads identically.
 *
 * Fully keyboard-operable per the WAI-ARIA radiogroup pattern: only the selected option is in the
 * tab order (roving tabindex); Arrow keys move + select (direction-aware, so RTL feels natural);
 * Home/End jump to the ends. Token-styled, so it flips with theme/density/accent automatically.
 */
export function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
}: SegmentedControlProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function move(from: number, dir: 1 | -1) {
    const n = options.length;
    for (let step = 1; step <= n; step++) {
      const i = (from + dir * step + n) % n;
      if (!options[i].disabled) {
        refs.current[i]?.focus();
        onChange(options[i].value);
        return;
      }
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLButtonElement>, index: number) {
    const rtl = getComputedStyle(e.currentTarget).direction === "rtl";
    switch (e.key) {
      case "ArrowRight":
        e.preventDefault();
        move(index, rtl ? -1 : 1);
        break;
      case "ArrowLeft":
        e.preventDefault();
        move(index, rtl ? 1 : -1);
        break;
      case "ArrowDown":
        e.preventDefault();
        move(index, 1);
        break;
      case "ArrowUp":
        e.preventDefault();
        move(index, -1);
        break;
      case "Home":
        e.preventDefault();
        move(-1, 1);
        break;
      case "End":
        e.preventDefault();
        move(0, -1);
        break;
    }
  }

  const selectedIndex = options.findIndex((o) => o.value === value);

  return (
    <div className="segmented" role="radiogroup" aria-label={ariaLabel}>
      {options.map((o, i) => {
        const on = o.value === value;
        // Roving tabindex: the selected option (or the first, if none) is the single tab stop.
        const tabbable = on || (selectedIndex === -1 && i === 0);
        return (
          <button
            key={o.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={on}
            disabled={o.disabled}
            tabIndex={tabbable ? 0 : -1}
            className={on ? "segmented__opt segmented__opt--on" : "segmented__opt"}
            onClick={() => onChange(o.value)}
            onKeyDown={(e) => onKeyDown(e, i)}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
