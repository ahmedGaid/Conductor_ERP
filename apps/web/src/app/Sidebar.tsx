import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import { getMe } from "../api/identity";
import { useAsync } from "../hooks/useAsync";
import "./Sidebar.css";

interface NavItem {
  key: string;
  icon: string;
  to: string;
}

const PRIMARY: NavItem[] = [
  { key: "dashboard", icon: "⌂", to: "/" },
  { key: "sales", icon: "▸", to: "/sales" },
  { key: "purchasing", icon: "▾", to: "/purchasing" },
  { key: "inventory", icon: "▦", to: "/inventory" },
  { key: "accounting", icon: "▤", to: "/accounting" },
  { key: "workflows", icon: "⇄", to: "/workflows" },
];

// Roadmap modules — shown to convey scope, enabled as each stage lands.
const SOON: { key: string; icon: string }[] = [
  { key: "crm", icon: "◇" },
  { key: "reports", icon: "▥" },
];

function initials(name: string): string {
  return name.slice(0, 2).toUpperCase();
}

export function Sidebar() {
  const { t } = useTranslation();
  const { data: me } = useAsync(getMe, []);

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
          {PRIMARY.map(({ key, icon, to }) => (
            <li key={key}>
              <NavLink
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
                }
              >
                <span className="sidebar__icon" aria-hidden="true">
                  {icon}
                </span>
                <span>{t(`nav.${key}`)}</span>
              </NavLink>
            </li>
          ))}
        </ul>

        <div className="sidebar__group-label">{t("nav.modulesSoon")}</div>
        <ul className="sidebar__list">
          {SOON.map(({ key, icon }) => (
            <li key={key}>
              <span className="sidebar__link sidebar__link--soon" aria-disabled="true">
                <span className="sidebar__icon" aria-hidden="true">
                  {icon}
                </span>
                <span>{t(`nav.${key}`)}</span>
                <span className="sidebar__badge">{t("common.soon")}</span>
              </span>
            </li>
          ))}
        </ul>
      </nav>

      <div className="sidebar__user">
        <span className="sidebar__avatar" aria-hidden="true">
          {initials(me?.username ?? "?")}
        </span>
        <span className="sidebar__user-meta">
          <span className="sidebar__user-name latin">{me?.username ?? "—"}</span>
          <span className="sidebar__user-role">{me?.roles?.[0] ?? ""}</span>
        </span>
      </div>
    </aside>
  );
}
