import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import "./AccountingNav.css";

const TABS: { key: string; to: string; end?: boolean }[] = [
  { key: "chart", to: "/accounting", end: true },
  { key: "journals", to: "/accounting/journals" },
  { key: "newEntry", to: "/accounting/journals/new" },
  { key: "trialBalance", to: "/accounting/trial-balance" },
  { key: "generalLedger", to: "/accounting/general-ledger" },
  { key: "incomeStatement", to: "/accounting/income-statement" },
  { key: "balanceSheet", to: "/accounting/balance-sheet" },
  { key: "cashFlow", to: "/accounting/cash-flow" },
  { key: "vatReturn", to: "/accounting/vat-return" },
  { key: "fixedAssets", to: "/accounting/assets" },
  { key: "costCenters", to: "/accounting/cost-centers" },
  { key: "bankRec", to: "/accounting/bank-reconciliation" },
  { key: "budgets", to: "/accounting/budgets" },
];

export function AccountingNav() {
  const { t } = useTranslation();
  return (
    <nav className="acctnav" aria-label={t("nav.accounting")}>
      {TABS.map(({ key, to, end }) => (
        <NavLink
          key={key}
          to={to}
          end={end}
          className={({ isActive }) => (isActive ? "acctnav__tab acctnav__tab--active" : "acctnav__tab")}
        >
          {t(`accounting.tabs.${key}`)}
        </NavLink>
      ))}
    </nav>
  );
}
