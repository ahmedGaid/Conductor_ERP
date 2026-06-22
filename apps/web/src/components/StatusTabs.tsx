import { useMemo, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { SegmentedControl, type SegmentedOption } from "./SegmentedControl";

/** Sentinel value for the leading "All" tab — never collides with a real status key. */
export const ALL_TAB = "__all__";

export interface StatusTab {
  value: string;
  label: string;
}

interface StatusTabsProps<T> {
  /**
   * The rows the counts are computed over. Pass the set *after* other filters
   * (e.g. the FilterBar result) so each tab's badge reflects the current view,
   * but *before* this tab's own selection is applied.
   */
  rows: T[];
  /** The status buckets, in display order. The "All" tab is prepended automatically. */
  tabs: StatusTab[];
  /** Reads the status value off a row, matched against each tab's `value`. */
  accessor: (row: T) => string;
  /** Active tab — {@link ALL_TAB} or one of `tabs[].value`. */
  value: string;
  onChange: (value: string) => void;
  /** Group label for assistive tech. */
  ariaLabel: string;
  /** Drop status tabs whose count is zero (the active one always stays). Default true. */
  hideEmpty?: boolean;
}

/**
 * List tabs with live count badges — the quick filter that sits above a record table
 * ("All 24 · Draft 8 · Confirmed 12"). A thin wrapper over {@link SegmentedControl}, so it
 * inherits the radiogroup keyboard model and token styling; it only adds the counting and the
 * neutral count pill. Complementary to the FilterBar: tabs are the one-click primary-status cut,
 * the FilterBar handles arbitrary fields. Counts are plain numbers (Latin digits, tabular).
 */
export function StatusTabs<T>({
  rows,
  tabs,
  accessor,
  value,
  onChange,
  ariaLabel,
  hideEmpty = true,
}: StatusTabsProps<T>) {
  const { t } = useTranslation();

  const counts = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of rows) {
      const k = accessor(r);
      m.set(k, (m.get(k) ?? 0) + 1);
    }
    return m;
  }, [rows, accessor]);

  const options = useMemo<SegmentedOption<string>[]>(() => {
    const visible = hideEmpty
      ? tabs.filter((tb) => (counts.get(tb.value) ?? 0) > 0 || tb.value === value)
      : tabs;
    return [
      { value: ALL_TAB, label: tabLabel(t("common.all"), rows.length) },
      ...visible.map((tb) => ({ value: tb.value, label: tabLabel(tb.label, counts.get(tb.value) ?? 0) })),
    ];
  }, [tabs, counts, rows.length, hideEmpty, value, t]);

  return (
    <div className="list-tabs">
      <SegmentedControl value={value} options={options} onChange={onChange} ariaLabel={ariaLabel} />
    </div>
  );
}

function tabLabel(text: string, count: number): ReactNode {
  return (
    <>
      {text}
      <span className="segmented__count">{count}</span>
    </>
  );
}
