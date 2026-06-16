import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { LanguageSwitcher } from "./LanguageSwitcher";
import "./CommandBar.css";

export function CommandBar({ onMenu }: { onMenu?: () => void }) {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="commandbar">
      <button
        type="button"
        className="btn btn--ghost btn--icon commandbar__menu"
        onClick={onMenu}
        aria-label={t("shell.openMenu")}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.8}
          strokeLinecap="round"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M3 6h18" />
          <path d="M3 12h18" />
          <path d="M3 18h18" />
        </svg>
      </button>
      <label className="commandbar__search">
        <span className="visually-hidden">{t("shell.search")}</span>
        <span className="commandbar__search-icon" aria-hidden="true">
          ⌕
        </span>
        <input
          type="search"
          className="commandbar__input"
          placeholder={t("shell.commandPlaceholder")}
        />
        <kbd className="commandbar__kbd latin">⌘K</kbd>
      </label>

      <div className="commandbar__actions">
        <LanguageSwitcher />
        <button
          type="button"
          className="btn btn--primary btn--icon commandbar__new"
          title={t("accounting.tabs.newEntry")}
          onClick={() => navigate("/accounting/journals/new")}
          aria-label={t("accounting.tabs.newEntry")}
        >
          +
        </button>
        <span className="commandbar__aux">
          <button type="button" className="btn btn--ghost btn--icon" aria-label={t("shell.notifications")}>
            ◔
          </button>
          <button type="button" className="btn btn--ghost btn--icon" aria-label={t("shell.help")}>
            ?
          </button>
        </span>
        <button type="button" className="btn btn--sm" onClick={logout}>
          {t("shell.logout")}
        </button>
      </div>
    </header>
  );
}
