import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import "./einvoice.css";

const TABS: { key: string; to: string; end?: boolean }[] = [
  { key: "invoices", to: "/einvoice", end: true },
];

export function EInvoiceNav() {
  const { t } = useTranslation();
  return (
    <nav className="ein-nav" aria-label={t("nav.einvoice")}>
      {TABS.map(({ key, to, end }) => (
        <NavLink
          key={key}
          to={to}
          end={end}
          className={({ isActive }) => (isActive ? "ein-nav__tab ein-nav__tab--active" : "ein-nav__tab")}
        >
          {t(`einvoice.tabs.${key}`)}
        </NavLink>
      ))}
    </nav>
  );
}
