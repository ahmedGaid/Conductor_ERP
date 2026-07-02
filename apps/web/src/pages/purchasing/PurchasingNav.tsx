import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import { assistantStatus } from "../../api/assistant";
import { useAsync } from "../../hooks/useAsync";
import "./purchasing.css";

const TABS: { key: string; to: string; end?: boolean }[] = [
  { key: "orders", to: "/purchasing", end: true },
  { key: "requests", to: "/purchasing/requests" },
  { key: "newOrder", to: "/purchasing/orders/new" },
  { key: "suppliers", to: "/purchasing/suppliers" },
];

// The AI tab only exists when the assistant is enabled on this install (no key ⇒ no AI surfaces).
const IMPORT_TAB: (typeof TABS)[number] = { key: "importInvoice", to: "/purchasing/orders/import" };

export function PurchasingNav() {
  const { t } = useTranslation();
  const { data: assistant } = useAsync(assistantStatus, [], "assistant:status");
  const tabs = assistant?.enabled ? [...TABS, IMPORT_TAB] : TABS;
  return (
    <header className="module-head">
      <h1 className="module-head__title">{t("nav.purchasing")}</h1>
      <p className="module-head__desc">{t("moduleIntro.purchasing")}</p>
      <nav className="pur-nav" aria-label={t("nav.purchasing")}>
      {tabs.map(({ key, to, end }) => (
        <NavLink
          key={key}
          to={to}
          end={end}
          className={({ isActive }) => (isActive ? "pur-nav__tab pur-nav__tab--active" : "pur-nav__tab")}
        >
          {t(`purchasing.tabs.${key}`)}
        </NavLink>
      ))}
      </nav>
    </header>
  );
}
