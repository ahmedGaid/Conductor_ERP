import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import "./notifications.css";

const TABS: { key: string; to: string; end?: boolean }[] = [
  { key: "log", to: "/notifications", end: true },
];

export function NotificationsNav() {
  const { t } = useTranslation();
  return (
    <nav className="ntf-nav" aria-label={t("nav.notifications")}>
      {TABS.map(({ key, to, end }) => (
        <NavLink
          key={key}
          to={to}
          end={end}
          className={({ isActive }) => (isActive ? "ntf-nav__tab ntf-nav__tab--active" : "ntf-nav__tab")}
        >
          {t(`notifications.tabs.${key}`)}
        </NavLink>
      ))}
    </nav>
  );
}
