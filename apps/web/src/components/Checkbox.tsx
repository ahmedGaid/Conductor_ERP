import { NavIcon } from "../app/icons";
import "./Checkbox.css";

/**
 * Monochrome selection checkbox — the one box used for row/bulk selection across every list.
 * Unchecked = an empty bordered square; checked = the owned `check` glyph; `indeterminate` = the
 * owned `minus` glyph (a select-all header when only some rows are picked). Colour stays out of the
 * box: the filled state is brand near-black, not an accent — selection is chrome, not status.
 *
 * Wraps a real <input type="checkbox"> for keyboard + a11y; the visual box is drawn on top.
 */
export function Checkbox({
  checked,
  indeterminate = false,
  onChange,
  label,
}: {
  checked: boolean;
  indeterminate?: boolean;
  onChange: (next: boolean, shiftKey: boolean) => void;
  /** Accessible label — visually hidden, read by screen readers. */
  label: string;
}) {
  return (
    <label className="checkbox">
      <input
        type="checkbox"
        className="checkbox__input"
        checked={checked}
        aria-label={label}
        ref={(el) => {
          if (el) el.indeterminate = indeterminate;
        }}
        onChange={(e) => onChange(e.target.checked, (e.nativeEvent as MouseEvent).shiftKey)}
        onClick={(e) => e.stopPropagation()}
      />
      <span className="checkbox__box" aria-hidden="true">
        {indeterminate ? <NavIcon name="minus" /> : checked ? <NavIcon name="check" /> : null}
      </span>
    </label>
  );
}
