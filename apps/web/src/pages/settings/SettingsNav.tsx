import { useTranslation } from "react-i18next";
import { NavLink, useLocation } from "react-router-dom";

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

// These tabs change data every user in the org sees or is bound by — the opposite of "yours
// alone" (brand-philosophy-review §04i P1). Their path prefixes drive which intro line shows.
const ORG_WIDE_PATHS = [
  "/settings/organization",
  "/settings/branches",
  "/settings/webhooks",
  "/settings/custom-fields",
  "/settings/developers",
  "/settings/einvoice",
  "/settings/system",
  "/settings/ai-usage",
];

export function SettingsNav() {
  const { t } = useTranslation();
  const { data: me } = useAsync(getMe, []);
  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;
  const location = useLocation();
  const isOrgWideTab = ORG_WIDE_PATHS.some((path) => location.pathname.startsWith(path));

  return (
    <header className="module-head">
      <h1 className="module-head__title">{t("settings.title")}</h1>
      <p className="module-head__desc">
        {t(isOrgWideTab ? "settings.introOrg" : "settings.introPersonal")}
      </p>
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
        {isAdmin && (
          <NavLink
            to="/settings/branches"
            className={({ isActive }) => (isActive ? "setnav__tab setnav__tab--active" : "setnav__tab")}
          >
            {t("settings.tabs.branches")}
          </NavLink>
        )}
        {isAdmin && (
          <NavLink
            to="/settings/webhooks"
            className={({ isActive }) => (isActive ? "setnav__tab setnav__tab--active" : "setnav__tab")}
          >
            {t("settings.tabs.webhooks")}
          </NavLink>
        )}
        {isAdmin && (
          <NavLink
            to="/settings/custom-fields"
            className={({ isActive }) => (isActive ? "setnav__tab setnav__tab--active" : "setnav__tab")}
          >
            {t("settings.tabs.customFields")}
          </NavLink>
        )}
        {isAdmin && (
          <NavLink
            to="/settings/developers"
            className={({ isActive }) => (isActive ? "setnav__tab setnav__tab--active" : "setnav__tab")}
          >
            {t("settings.tabs.developers")}
          </NavLink>
        )}
        {isAdmin && (
          <NavLink
            to="/settings/einvoice"
            className={({ isActive }) => (isActive ? "setnav__tab setnav__tab--active" : "setnav__tab")}
          >
            {t("settings.tabs.einvoice")}
          </NavLink>
        )}
        {isAdmin && (
          <NavLink
            to="/settings/system"
            className={({ isActive }) => (isActive ? "setnav__tab setnav__tab--active" : "setnav__tab")}
          >
            {t("settings.tabs.system")}
          </NavLink>
        )}
        {isAdmin && (
          <NavLink
            to="/settings/ai-usage"
            className={({ isActive }) => (isActive ? "setnav__tab setnav__tab--active" : "setnav__tab")}
          >
            {t("settings.tabs.aiUsage")}
          </NavLink>
        )}
      </nav>
    </header>
  );
}
