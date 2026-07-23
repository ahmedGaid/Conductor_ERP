import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import "./WorkflowNav.css";

const TABS: { key: string; to: string; label?: string; end?: boolean }[] = [
  { key: "workflows", to: "/workflows", end: true },
  { key: "instances", to: "/workflows/instances" },
];

export function WorkflowNav() {
  const { t } = useTranslation();
  return (
    <header className="module-head">
      <h1 className="module-head__title">{t("nav.workflows")}</h1>
      <p className="module-head__desc">{t("moduleIntro.workflows")}</p>
      <nav className="wfnav" aria-label={t("nav.workflows")}>
        {TABS.map(({ key, to, end, label }) => (
          <NavLink
            key={key}
            to={to}
            end={end}
            className={({ isActive }) => (isActive ? "wfnav__tab wfnav__tab--active" : "wfnav__tab")}
          >
            {t(label ?? `workflow.tabs.${key}`)}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}
