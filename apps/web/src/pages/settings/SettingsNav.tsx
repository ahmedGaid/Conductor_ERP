import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import { getMe } from "../../api/identity";
import { useAsync } from "../../hooks/useAsync";
import { SYSTEM_ADMIN } from "./roles";
import "./settings.css";

const TABS: { key: string; to: string; end?: boolean }[] = [
  { key: "profile", to: "/settings/profile" },
  { key: "appearance", to: "/settings/appearance" },
  { key: "dashboard", to: "/settings/dashboard" },
  { key: "navigation", to: "/settings/navigation" },
  { key: "notifications", to: "/settings/notifications" },
  { key: "accessibility", to: "/settings/accessibility" },
];

export function SettingsNav() {
  const { t } = useTranslation();
  const { data: me } = useAsync(getMe, []);
  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;

  return (
    <header className="module-head">
      <h1 className="module-head__title">{t("settings.title")}</h1>
      <p className="module-head__desc">{t("settings.intro")}</p>
      <nav className="setnav" aria-label={t("settings.title")}>
        {TABS.map(({ key, to, end }) => (
          <NavLink
            key={key}
            to={to}
            end={end}
            className={({ isActive }) => (isActive ? "setnav__tab setnav__tab--active" : "setnav__tab")}
          >
            {t(`settings.tabs.${key}`)}
          </NavLink>
        ))}
        {isAdmin && (
          <NavLink
            to="/settings/organization"
            className={({ isActive }) => (isActive ? "setnav__tab setnav__tab--active" : "setnav__tab")}
          >
            {t("settings.tabs.organization")}
          </NavLink>
        )}
      </nav>
    </header>
  );
}
