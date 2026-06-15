import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import "./sales.css";

const TABS: { key: string; to: string; end?: boolean }[] = [
  { key: "orders", to: "/sales", end: true },
  { key: "newOrder", to: "/sales/orders/new" },
  { key: "customers", to: "/sales/customers" },
];

export function SalesNav() {
  const { t } = useTranslation();
  return (
    <nav className="sales-nav" aria-label={t("nav.sales")}>
      {TABS.map(({ key, to, end }) => (
        <NavLink
          key={key}
          to={to}
          end={end}
          className={({ isActive }) => (isActive ? "sales-nav__tab sales-nav__tab--active" : "sales-nav__tab")}
        >
          {t(`sales.tabs.${key}`)}
        </NavLink>
      ))}
    </nav>
  );
}
