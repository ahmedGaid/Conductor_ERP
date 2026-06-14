import { useTranslation } from "react-i18next";

import "./Sidebar.css";

type NavKey = "dashboard" | "workflows" | "forms" | "settings";

const NAV_ITEMS: { key: NavKey; icon: string }[] = [
  { key: "dashboard", icon: "▣" },
  { key: "workflows", icon: "⇄" },
  { key: "forms", icon: "▤" },
  { key: "settings", icon: "⚙" },
];

export function Sidebar({ active = "dashboard" }: { active?: NavKey }) {
  const { t } = useTranslation();

  return (
    <nav className="sidebar" aria-label={t("nav.dashboard")}>
      <div className="sidebar__brand">{t("app.title")}</div>
      <ul className="sidebar__list">
        {NAV_ITEMS.map(({ key, icon }) => (
          <li key={key}>
            <a
              className="sidebar__link"
              href={`#/${key}`}
              aria-current={key === active ? "page" : undefined}
            >
              <span className="sidebar__icon" aria-hidden="true">
                {icon}
              </span>
              <span>{t(`nav.${key}`)}</span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
