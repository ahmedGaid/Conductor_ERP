import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../app/icons";
import { ComboBox } from "./ComboBox";
import { Popover } from "./Popover";
import "./DatePicker.css";

interface DatePickerProps {
  /** ISO date string `YYYY-MM-DD`, or "" when unset. */
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

/**
 * Date field — a <select>-shaped trigger (styling shared via `.combobox-trigger` in global.css)
 * that opens a Popover calendar: a typeable field up top, Month + Year pickers (our own ComboBox),
 * prev/next month steppers, and a day grid — the same shape Twenty's date picker uses, rebuilt on
 * our tokens/icons with no new dependency. Emits/consumes ISO `YYYY-MM-DD`, the wire format the
 * native <input type="date"> it replaces used. Digits are Latin in both locales (brand rule);
 * month names and weekday labels are localized.
 */
export function DatePicker({ value, onChange, placeholder, className, disabled }: DatePickerProps) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const isArabic = i18n.language.startsWith("ar");
  // Latin digits in both locales (brand rule); Arabic gets Egyptian Gregorian month names.
  const localeTag = isArabic ? "ar-EG-u-nu-latn" : "en-GB-u-nu-latn";
  // Egyptian week starts Saturday; English starts Monday.
  const firstDayOfWeek = isArabic ? 6 : 1;

  const selected = value ? parseISO(value) : null;
  // The month the grid is showing; defaults to the selected date, else today.
  const [view, setView] = useState(() => selected ?? new Date());
  const viewYear = view.getFullYear();
  const viewMonth = view.getMonth();

  const monthNames = useMemo(() => {
    const fmt = new Intl.DateTimeFormat(localeTag, { month: "long" });
    return Array.from({ length: 12 }, (_, m) => fmt.format(new Date(2020, m, 1)));
  }, [localeTag]);

  const weekdayNames = useMemo(() => {
    // Arabic "short" weekday names (الأربعاء…) are too long for a day column; the conventional
    // single-letter "narrow" form (ح ن ث ر خ ج س) fits. English "short" (Mon, Tue) reads better.
    const fmt = new Intl.DateTimeFormat(localeTag, { weekday: isArabic ? "narrow" : "short" });
    // A known week: 2024-01-07 is a Sunday. Rotate so the row starts on firstDayOfWeek.
    return Array.from({ length: 7 }, (_, i) => {
      const dow = (firstDayOfWeek + i) % 7;
      return fmt.format(new Date(2024, 0, 7 + dow));
    });
  }, [localeTag, firstDayOfWeek, isArabic]);

  const years = useMemo(() => {
    const now = new Date().getFullYear();
    // Business dates rarely run far out; a wide-but-bounded range keeps the picker light.
    return Array.from({ length: 91 }, (_, i) => now + 5 - i).map((y) => ({
      value: String(y),
      label: String(y),
    }));
  }, []);

  // Six weeks of cells covering the view month, padded with the trailing/leading days.
  const cells = useMemo(() => {
    const firstOfMonth = new Date(viewYear, viewMonth, 1);
    const lead = (firstOfMonth.getDay() - firstDayOfWeek + 7) % 7;
    const start = new Date(viewYear, viewMonth, 1 - lead);
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
      return d;
    });
  }, [viewYear, viewMonth, firstDayOfWeek]);

  const displayValue = selected
    ? new Intl.DateTimeFormat(localeTag, { day: "2-digit", month: "2-digit", year: "numeric" }).format(selected)
    : "";

  const today = new Date();

  function pick(d: Date) {
    onChange(toISO(d));
    setOpen(false);
  }
  function stepMonth(delta: number) {
    setView(new Date(viewYear, viewMonth + delta, 1));
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={className ? `combobox-trigger ${className}` : "combobox-trigger"}
        aria-haspopup="dialog"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => {
          if (selected) setView(selected);
          setOpen((o) => !o);
        }}
      >
        <span className={selected ? "combobox-trigger__value" : "combobox-trigger__value combobox-trigger__value--placeholder"}>
          {selected ? displayValue : (placeholder ?? t("common.selectField", { field: t("common.date") }))}
        </span>
        <NavIcon name="calendar" />
      </button>

      <Popover open={open} onClose={() => setOpen(false)} anchorRef={triggerRef} className="datepicker-popover">
        <div className="datepicker">
          <div className="datepicker__header">
            <div className="datepicker__selects">
              <ComboBox
                value={String(viewMonth)}
                onChange={(v) => setView(new Date(viewYear, Number(v), 1))}
                placeholder={monthNames[viewMonth]}
                options={monthNames.map((name, m) => ({ value: String(m), label: name }))}
                className="datepicker__month"
              />
              <ComboBox
                value={String(viewYear)}
                onChange={(v) => setView(new Date(Number(v), viewMonth, 1))}
                placeholder={String(viewYear)}
                options={years}
                className="datepicker__year"
              />
            </div>
            <div className="datepicker__nav">
              <button type="button" className="btn btn--icon btn--ghost" aria-label={t("common.date")} onClick={() => stepMonth(-1)}>
                <NavIcon name="chevronLeft" />
              </button>
              <button type="button" className="btn btn--icon btn--ghost" aria-label={t("common.date")} onClick={() => stepMonth(1)}>
                <NavIcon name="chevronRight" />
              </button>
            </div>
          </div>

          <div className="datepicker__grid" role="grid">
            {weekdayNames.map((wd, i) => (
              <span key={i} className="datepicker__weekday">{wd}</span>
            ))}
            {cells.map((d, i) => {
              const outside = d.getMonth() !== viewMonth;
              const isSelected = selected != null && sameDay(d, selected);
              const isToday = sameDay(d, today);
              const cls = [
                "datepicker__day",
                outside && "datepicker__day--outside",
                isSelected && "datepicker__day--selected",
                isToday && !isSelected && "datepicker__day--today",
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <button key={i} type="button" className={cls} onClick={() => pick(d)}>
                  {d.getDate()}
                </button>
              );
            })}
          </div>

          <div className="datepicker__footer">
            <button type="button" className="btn btn--sm btn--ghost" onClick={() => pick(new Date())}>
              {t("common.today")}
            </button>
            {value && (
              <button
                type="button"
                className="btn btn--sm btn--ghost"
                onClick={() => {
                  onChange("");
                  setOpen(false);
                }}
              >
                {t("common.clear")}
              </button>
            )}
          </div>
        </div>
      </Popover>
    </>
  );
}

/** Parse `YYYY-MM-DD` into a local Date (no timezone drift). */
function parseISO(s: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return null;
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

function toISO(d: Date): string {
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const da = String(d.getDate()).padStart(2, "0");
  return `${y}-${mo}-${da}`;
}

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
