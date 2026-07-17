import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../app/icons";
import { Popover } from "./Popover";
import "./ComboBox.css";

export interface ComboBoxOption {
  value: string;
  label: string;
}

interface ComboBoxProps {
  options: readonly ComboBoxOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  className?: string;
  disabled?: boolean;
  "aria-label"?: string;
}

/**
 * Searchable single-select: a <select>-shaped trigger (styling shared via the `.combobox-trigger`
 * join in styles/global.css) that opens the same search + check-mark list FilterBar's value picker
 * uses (popover__menu/__item/__check), so this reads as one component family, not a new pattern.
 * Filters client-side on `label`; the emitted value is still the option's `value` (a code), same
 * contract as the native <select> it replaces.
 */
export function ComboBox({
  options,
  value,
  onChange,
  placeholder,
  className,
  disabled,
  "aria-label": ariaLabel,
}: ComboBoxProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const triggerRef = useRef<HTMLButtonElement>(null);

  const selected = options.find((o) => o.value === value);
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return options;
    return options.filter((o) => o.label.toLowerCase().includes(q));
  }, [options, search]);

  function pick(v: string) {
    onChange(v);
    setOpen(false);
    setSearch("");
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={className ? `combobox-trigger ${className}` : "combobox-trigger"}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
      >
        <span
          className={
            selected ? "combobox-trigger__value" : "combobox-trigger__value combobox-trigger__value--placeholder"
          }
        >
          {selected ? selected.label : placeholder}
        </span>
        <NavIcon name="chevronDown" />
      </button>

      <Popover
        open={open}
        onClose={() => {
          setOpen(false);
          setSearch("");
        }}
        anchorRef={triggerRef}
        className="combobox-popover"
      >
        <div className="popover__menu">
          <input
            type="text"
            className="popover__search"
            autoFocus
            placeholder={t("common.search")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {filtered.length === 0 && <p className="popover__empty">{t("common.noResults")}</p>}
          {filtered.map((o) => (
            <button
              key={o.value}
              type="button"
              className={o.value === value ? "popover__item popover__item--on" : "popover__item"}
              onClick={() => pick(o.value)}
            >
              {o.label}
              {o.value === value && (
                <span className="popover__check" aria-hidden="true">
                  <NavIcon name="check" />
                </span>
              )}
            </button>
          ))}
        </div>
      </Popover>
    </>
  );
}
