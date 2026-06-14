import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import "./Sidebar.css";

type NavKey = "dashboard" | "workflows" | "accounting" | "forms" | "settings";

const NAV_ITEMS: { key: NavKey; icon: string; to: string }[] = [
  { key: "dashboard", icon: "▣", to: "/" },
  { key: "workflows", icon: "⇄", to: "/workflows" },
  { key: "accounting", icon: "Σ", to: "/accounting" },
  { key: "forms", icon: "▤", to: "/forms" },
  { key: "settings", icon: "⚙", to: "/settings" },
];

export function Sidebar() {
  const { t } = useTranslation();

  return (
    <nav className="sidebar" aria-label={t("nav.dashboard")}>
      <div className="sidebar__brand">{t("app.title")}</div>
      <ul className="sidebar__list">
        {NAV_ITEMS.map(({ key, icon, to }) => (
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
    </nav>
  );
}
