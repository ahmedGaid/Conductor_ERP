import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import "./crm.css";

const TABS: { key: string; to: string; end?: boolean }[] = [
  { key: "pipeline", to: "/crm", end: true },
  { key: "leads", to: "/crm/leads" },
  { key: "tickets", to: "/crm/tickets" },
  { key: "campaigns", to: "/crm/campaigns" },
];

export function CrmNav() {
  const { t } = useTranslation();
  return (
    <header className="module-head">
      <h1 className="module-head__title">{t("nav.crm")}</h1>
      <p className="module-head__desc">{t("moduleIntro.crm")}</p>
      <nav className="crm-nav" aria-label={t("nav.crm")}>
      {TABS.map(({ key, to, end }) => (
        <NavLink
          key={key}
          to={to}
          end={end}
          className={({ isActive }) => (isActive ? "crm-nav__tab crm-nav__tab--active" : "crm-nav__tab")}
        >
          {t(`crm.tabs.${key}`)}
        </NavLink>
      ))}
      </nav>
    </header>
  );
}
