import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import { getMe } from "../api/identity";
import { usePreferences } from "../preferences/PreferencesContext";
import { useAsync } from "../hooks/useAsync";
import { SYSTEM_ADMIN } from "../pages/settings/roles";
import { NavIcon } from "./icons";
import "./Sidebar.css";

interface NavItem {
  key: string;
  to: string;
}

const PRIMARY: NavItem[] = [
  { key: "dashboard", to: "/" },
  { key: "sales", to: "/sales" },
  { key: "purchasing", to: "/purchasing" },
  { key: "inventory", to: "/inventory" },
  { key: "accounting", to: "/accounting" },
  { key: "einvoice", to: "/einvoice" },
  { key: "crm", to: "/crm" },
  { key: "workflows", to: "/workflows" },
];

// Roadmap modules — shown to convey scope, enabled as each stage lands.
const SOON: { key: string }[] = [{ key: "reports" }];

function initials(name: string): string {
  return name.slice(0, 2).toUpperCase();
}

export function Sidebar() {
  const { t } = useTranslation();
  const { data: me } = useAsync(getMe, []);
  const { prefs } = usePreferences();
  const favorites = prefs?.favorites ?? [];
  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__logo" aria-hidden="true">
          C
        </span>
        <span className="sidebar__wordmark">{t("app.title")}</span>
      </div>

      <nav className="sidebar__nav" aria-label={t("nav.dashboard")}>
        <ul className="sidebar__list">
          {PRIMARY.map(({ key, to }) => (
            <li key={key}>
              <NavLink
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
                }
              >
                <span className="sidebar__icon">
                  <NavIcon name={key} />
                </span>
                <span>{t(`nav.${key}`)}</span>
              </NavLink>
            </li>
          ))}
        </ul>

        {favorites.length > 0 && (
          <>
            <div className="sidebar__group-label">{t("nav.favorites")}</div>
            <ul className="sidebar__list">
              {favorites.map((fav) => (
                <li key={fav.to}>
                  <NavLink
                    to={fav.to}
                    end={fav.to === "/"}
                    className={({ isActive }) =>
                      isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
                    }
                  >
                    <span className="sidebar__icon" aria-hidden="true">★</span>
                    <span>{t(fav.label)}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </>
        )}

        {isAdmin && (
          <>
            <div className="sidebar__group-label">{t("nav.administration")}</div>
            <ul className="sidebar__list">
              <li>
                <NavLink
                  to="/admin/users"
                  className={({ isActive }) =>
                    isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
                  }
                >
                  <span className="sidebar__icon"><NavIcon name="crm" /></span>
                  <span>{t("nav.usersAdmin")}</span>
                </NavLink>
              </li>
              <li>
                <NavLink
                  to="/admin/roles"
                  className={({ isActive }) =>
                    isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
                  }
                >
                  <span className="sidebar__icon"><NavIcon name="settings" /></span>
                  <span>{t("nav.rolesAdmin")}</span>
                </NavLink>
              </li>
            </ul>
          </>
        )}

        <div className="sidebar__group-label">{t("nav.modulesSoon")}</div>
        <ul className="sidebar__list">
          {SOON.map(({ key }) => (
            <li key={key}>
              <span className="sidebar__link sidebar__link--soon" aria-disabled="true">
                <span className="sidebar__icon">
                  <NavIcon name={key} />
                </span>
                <span>{t(`nav.${key}`)}</span>
                <span className="sidebar__badge">{t("common.soon")}</span>
              </span>
            </li>
          ))}
        </ul>
      </nav>

      <NavLink
        to="/settings"
        className={({ isActive }) =>
          isActive ? "sidebar__user sidebar__user--active" : "sidebar__user"
        }
        title={t("settings.title")}
      >
        <span className="sidebar__avatar" aria-hidden="true">
          {initials(prefs?.display_name || me?.username || "?")}
        </span>
        <span className="sidebar__user-meta">
          <span className="sidebar__user-name latin">
            {prefs?.display_name || me?.username || "—"}
          </span>
          <span className="sidebar__user-role">{me?.roles?.[0] ?? ""}</span>
        </span>
        <span className="sidebar__user-cog" aria-hidden="true">
          <NavIcon name="settings" />
        </span>
      </NavLink>
    </aside>
  );
}
