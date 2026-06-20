// The dashboard's optional panels, in default order. The Dashboard settings tab reorders/hides
// these (persisted to UserPreferences.dashboard_layout); DashboardPage renders them via
// orderedVisibleWidgets so the two stay in sync from one registry.

export interface DashboardLayout {
  order?: string[];
  hidden?: string[];
}

// `key` maps to a panel in DashboardPage; `labelKey` is the i18n key for the settings list.
export const DASHBOARD_WIDGETS: { key: string; labelKey: string }[] = [
  { key: "attention", labelKey: "settings.dashboard.widgets.attention" },
  { key: "expenses", labelKey: "settings.dashboard.widgets.expenses" },
  { key: "cashflow", labelKey: "settings.dashboard.widgets.cashflow" },
  { key: "journals", labelKey: "settings.dashboard.widgets.journals" },
  { key: "shortcuts", labelKey: "settings.dashboard.widgets.shortcuts" },
];

const KEYS = DASHBOARD_WIDGETS.map((w) => w.key);

/** Visible widget keys in the user's chosen order (unknown keys dropped, missing ones appended). */
export function orderedVisibleWidgets(layout: DashboardLayout | undefined): string[] {
  const order = layout?.order ?? [];
  const hidden = new Set(layout?.hidden ?? []);
  const ordered = [...order.filter((k) => KEYS.includes(k)), ...KEYS.filter((k) => !order.includes(k))];
  return ordered.filter((k) => !hidden.has(k));
}
