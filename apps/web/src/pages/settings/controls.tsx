import type { ReactNode } from "react";

// Small, shared building blocks for the Settings tabs, so every row reads the same: a label +
// helper text on one side and the control on the other. All styling is token-driven (settings.css).

// The segmented control is one shared, app-wide component now; Settings keeps the familiar
// `Segmented` / `Option` names by re-exporting it, so its tabs need no change.
export { SegmentedControl as Segmented } from "../../components/SegmentedControl";
export type { SegmentedOption as Option } from "../../components/SegmentedControl";

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
