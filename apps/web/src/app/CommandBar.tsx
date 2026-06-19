import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useHelp } from "../help/HelpContext";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { ThemeToggle } from "./ThemeToggle";
import { CommandPalette } from "./CommandPalette";
import { NavIcon } from "./icons";
import "./CommandBar.css";

export function CommandBar({ onMenu }: { onMenu?: () => void }) {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const { openHelp } = useHelp();
  const navigate = useNavigate();
  const [paletteOpen, setPaletteOpen] = useState(false);

  // ⌘K / Ctrl+K opens the command palette from anywhere in the app.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        setPaletteOpen(true);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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
      <button
        type="button"
        className="commandbar__search"
        onClick={() => setPaletteOpen(true)}
        aria-haspopup="dialog"
        aria-label={t("shell.search")}
      >
        <span className="commandbar__search-icon" aria-hidden="true">⌕</span>
        <span className="commandbar__search-text">{t("shell.commandPlaceholder")}</span>
        <kbd className="commandbar__kbd latin">⌘K</kbd>
      </button>

      <div className="commandbar__actions">
        <ThemeToggle />
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
          <button
            type="button"
            className="btn btn--ghost btn--icon"
            aria-label={t("shell.notifications")}
            title={t("shell.notifications")}
            onClick={() => navigate("/notifications")}
          >
            <NavIcon name="notifications" />
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--icon"
            aria-label={t("shell.help")}
            title={t("shell.help")}
            onClick={openHelp}
          >
            ?
          </button>
        </span>
        <button type="button" className="btn btn--sm" onClick={logout}>
          {t("shell.logout")}
        </button>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </header>
  );
}
