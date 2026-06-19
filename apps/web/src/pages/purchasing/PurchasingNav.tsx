import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import "./purchasing.css";

const TABS: { key: string; to: string; end?: boolean }[] = [
  { key: "orders", to: "/purchasing", end: true },
  { key: "requests", to: "/purchasing/requests" },
  { key: "newOrder", to: "/purchasing/orders/new" },
  { key: "suppliers", to: "/purchasing/suppliers" },
];

export function PurchasingNav() {
  const { t } = useTranslation();
  return (
    <header className="module-head">
      <h1 className="module-head__title">{t("nav.purchasing")}</h1>
      <p className="module-head__desc">{t("moduleIntro.purchasing")}</p>
      <nav className="pur-nav" aria-label={t("nav.purchasing")}>
      {TABS.map(({ key, to, end }) => (
        <NavLink
          key={key}
          to={to}
          end={end}
          className={({ isActive }) => (isActive ? "pur-nav__tab pur-nav__tab--active" : "pur-nav__tab")}
        >
          {t(`purchasing.tabs.${key}`)}
        </NavLink>
      ))}
      </nav>
    </header>
  );
}
