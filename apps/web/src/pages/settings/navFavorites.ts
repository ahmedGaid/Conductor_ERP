// Destinations a user can pin as favorites. `label` is an i18n key (translated at render time, so
// favorites follow the active language); `to` is the route. NavigationSettingsPage toggles these
// into UserPreferences.favorites; the Sidebar renders that list as a "Favorites" group.

export interface FavoriteCandidate {
  label: string; // i18n key
  to: string;
}

export const FAVORITE_CANDIDATES: FavoriteCandidate[] = [
  { label: "nav.dashboard", to: "/" },
  { label: "nav.sales", to: "/sales" },
  { label: "nav.purchasing", to: "/purchasing" },
  { label: "nav.inventory", to: "/inventory" },
  { label: "nav.accounting", to: "/accounting" },
  { label: "nav.einvoice", to: "/einvoice" },
  { label: "nav.crm", to: "/crm" },
  { label: "nav.workflows", to: "/workflows" },
  { label: "nav.notifications", to: "/notifications" },
  { label: "command.trialBalance", to: "/accounting/trial-balance" },
  { label: "command.customers", to: "/sales/customers" },
  { label: "command.suppliers", to: "/purchasing/suppliers" },
  { label: "command.stockOnHand", to: "/inventory/stock-on-hand" },
];
