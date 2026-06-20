import type { ReactNode } from "react";

// Small, shared building blocks for the Settings tabs, so every row reads the same: a label +
// helper text on one side and the control on the other. All styling is token-driven (settings.css).

export function SettingRow({
  title,
  desc,
  htmlFor,
  children,
}: {
  title: string;
  desc?: string;
  htmlFor?: string;
  children: ReactNode;
}) {
  return (
    <div className="setrow">
      <div className="setrow__label">
        <label className="setrow__title" htmlFor={htmlFor}>
          {title}
        </label>
        {desc && <p className="setrow__desc">{desc}</p>}
      </div>
      <div className="setrow__control">{children}</div>
    </div>
  );
}

export interface Option<T extends string> {
  value: T;
  label: string;
}

/** A horizontal radio group rendered as pill buttons (single choice). */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
}: {
  value: T;
  options: Option<T>[];
  onChange: (value: T) => void;
  ariaLabel: string;
}) {
  return (
    <div className="segmented" role="radiogroup" aria-label={ariaLabel}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          className={o.value === value ? "segmented__opt segmented__opt--on" : "segmented__opt"}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** An on/off switch (a styled checkbox). */
export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      className={checked ? "switch switch--on" : "switch"}
      onClick={() => onChange(!checked)}
    >
      <span className="switch__knob" aria-hidden="true" />
    </button>
  );
}
