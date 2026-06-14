import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import { LanguageSwitcher } from "./LanguageSwitcher";
import "./CommandBar.css";

export function CommandBar() {
  const { t } = useTranslation();
  const { logout } = useAuth();

  return (
    <header className="commandbar">
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
      </label>
      <div className="commandbar__actions">
        <LanguageSwitcher />
        <button className="btn btn--sm" type="button" onClick={logout}>
          {t("shell.logout")}
        </button>
      </div>
    </header>
  );
}
