import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import "./inventory.css";

const TABS: { key: string; to: string; end?: boolean }[] = [
  { key: "stockOnHand", to: "/inventory", end: true },
  { key: "items", to: "/inventory/items" },
  { key: "warehouses", to: "/inventory/warehouses" },
  { key: "movements", to: "/inventory/movements" },
  { key: "counts", to: "/inventory/counts" },
  { key: "batches", to: "/inventory/batches" },
];

export function InventoryNav() {
  const { t } = useTranslation();
  return (
    <header className="module-head">
      <h1 className="module-head__title">{t("nav.inventory")}</h1>
      <p className="module-head__desc">{t("moduleIntro.inventory")}</p>
      <nav className="inv-nav" aria-label={t("nav.inventory")}>
      {TABS.map(({ key, to, end }) => (
        <NavLink
          key={key}
          to={to}
          end={end}
          className={({ isActive }) => (isActive ? "inv-nav__tab inv-nav__tab--active" : "inv-nav__tab")}
        >
          {t(`inventory.tabs.${key}`)}
        </NavLink>
      ))}
      </nav>
    </header>
  );
}
