import { type ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import { getMe } from "../api/identity";
import { usePreferences } from "../preferences/PreferencesContext";
import { useAsync } from "../hooks/useAsync";
import { SYSTEM_ADMIN } from "../pages/settings/roles";
import { Tooltip } from "../components/Tooltip";
import { SidebarIdentity } from "./SidebarIdentity";
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

// The `g`-leader shortcut for each destination, mirrored from useGlobalShortcuts so
// the sidebar advertises the exact keys that navigate there (shown in the hover tip).
const NAV_SHORTCUT: Record<string, string[]> = {
  dashboard: ["G", "D"],
  sales: ["G", "S"],
  purchasing: ["G", "P"],
  inventory: ["G", "I"],
  accounting: ["G", "A"],
  einvoice: ["G", "E"],
  crm: ["G", "C"],
  workflows: ["G", "W"],
};

// Roadmap modules — shown to convey scope, enabled as each stage lands.
const SOON: { key: string }[] = [{ key: "reports" }];

export function Sidebar() {
  const { t } = useTranslation();
  const { data: me } = useAsync(getMe, []);
  const { prefs, update } = usePreferences();
  const favorites = prefs?.favorites ?? [];
  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;
  const compact = prefs?.sidebar_style === "compact";

  // In the collapsed rail the labels are hidden, so each nav item grows a side tooltip to stay
  // identifiable. Expanded, the label is right there — no tooltip needed.
  const withTip = (label: string, node: ReactElement) =>
    compact ? (
      <Tooltip label={label} placement="inlineEnd">
        {node}
      </Tooltip>
    ) : (
      node
    );

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__logo" aria-hidden="true" />
        <span className="sidebar__wordmark">{t("app.title")}</span>
        <Tooltip label={compact ? t("nav.expandSidebar") : t("nav.collapseSidebar")} placement={compact ? "inlineEnd" : "bottom"}>
          <button
            type="button"
            className="sidebar__collapse"
            aria-label={compact ? t("nav.expandSidebar") : t("nav.collapseSidebar")}
            aria-expanded={!compact}
            onClick={() => update({ sidebar_style: compact ? "expanded" : "compact" })}
          >
            <NavIcon name="sidebar" />
          </button>
        </Tooltip>
      </div>

      <nav className="sidebar__nav" aria-label={t("nav.dashboard")}>
        <ul className="sidebar__list">
          {PRIMARY.filter(
            ({ key }) => key !== "einvoice" || prefs?.einvoice_enabled !== false,
          ).map(({ key, to }) => (
            <li key={key}>
              {/* Always tipped — even with the label visible — so the hover bubble can
                  advertise the g-shortcut (and double as the label in the compact rail). */}
              <Tooltip label={t(`nav.${key}`)} shortcut={NAV_SHORTCUT[key]} placement="inlineEnd">
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
              </Tooltip>
            </li>
          ))}
        </ul>

        {favorites.length > 0 && (
          <>
            <div className="sidebar__group-label">{t("nav.favorites")}</div>
            <ul className="sidebar__list">
              {favorites.map((fav) => (
                <li key={fav.to}>
                  {withTip(
                    t(fav.label),
                    <NavLink
                      to={fav.to}
                      end={fav.to === "/"}
                      className={({ isActive }) =>
                        isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
                      }
                    >
                      <span className="sidebar__icon" aria-hidden="true"><NavIcon name="star" /></span>
                      <span>{t(fav.label)}</span>
                    </NavLink>,
                  )}
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
                {withTip(
                  t("nav.pricing"),
                  <NavLink
                    to="/pricing"
                    className={({ isActive }) =>
                      isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
                    }
                  >
                    <span className="sidebar__icon"><NavIcon name="pricing" /></span>
                    <span>{t("nav.pricing")}</span>
                  </NavLink>,
                )}
              </li>
              <li>
                {withTip(
                  t("nav.usersAdmin"),
                  <NavLink
                    to="/admin/users"
                    className={({ isActive }) =>
                      isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
                    }
                  >
                    <span className="sidebar__icon"><NavIcon name="crm" /></span>
                    <span>{t("nav.usersAdmin")}</span>
                  </NavLink>,
                )}
              </li>
              <li>
                {withTip(
                  t("nav.rolesAdmin"),
                  <NavLink
                    to="/admin/roles"
                    className={({ isActive }) =>
                      isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
                    }
                  >
                    <span className="sidebar__icon"><NavIcon name="settings" /></span>
                    <span>{t("nav.rolesAdmin")}</span>
                  </NavLink>,
                )}
              </li>
            </ul>
          </>
        )}

        <div className="sidebar__group-label">{t("nav.modulesSoon")}</div>
        <ul className="sidebar__list">
          {SOON.map(({ key }) => (
            <li key={key}>
              {withTip(
                t(`nav.${key}`),
                <span className="sidebar__link sidebar__link--soon" aria-disabled="true">
                  <span className="sidebar__icon">
                    <NavIcon name={key} />
                  </span>
                  <span>{t(`nav.${key}`)}</span>
                  <span className="sidebar__badge">{t("common.soon")}</span>
                </span>,
              )}
            </li>
          ))}
        </ul>
      </nav>

      <SidebarIdentity
        companyName={prefs?.company_name?.trim() || t("app.title")}
        isAdmin={isAdmin}
      />
    </aside>
  );
}
