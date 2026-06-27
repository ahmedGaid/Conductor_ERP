import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { usePreferences } from "../preferences/PreferencesContext";
import { useGlobalShortcuts } from "../hooks/useGlobalShortcuts";
import { Tooltip } from "../components/Tooltip";
import { AppMenu } from "./AppMenu";
import { CommandPalette } from "./CommandPalette";
import { useShortcuts } from "./ShortcutsContext";
import { UserMenu } from "./UserMenu";
import { NavIcon } from "./icons";
import "./CommandBar.css";

export function CommandBar({ onMenu }: { onMenu?: () => void }) {
  const { t } = useTranslation();
  const { prefs } = usePreferences();
  const { openShortcuts } = useShortcuts();
  const navigate = useNavigate();
  const [paletteOpen, setPaletteOpen] = useState(false);

  // When e-invoicing is turned off in setup, hide it from every nav surface (sidebar, palette,
  // cheat-sheet and the g-key chord) so "disabled" reads consistently.
  const einvoiceEnabled = prefs?.einvoice_enabled !== false;

  // App-wide keyboard layer: ⌘K / `/` / `c` open the palette, `g`+key navigates,
  // `?` opens the cheat-sheet (mounted in the shell). Stable callback so the listener isn't re-bound.
  const openPalette = useCallback(() => setPaletteOpen(true), []);
  useGlobalShortcuts({ openPalette, openShortcuts, einvoiceEnabled });

  return (
    <header className="commandbar">
      <Tooltip label={t("shell.openMenu")} placement="bottom">
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
      </Tooltip>
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
        <Tooltip label={t("accounting.tabs.newEntry")} placement="bottom">
          <button
            type="button"
            className="btn btn--primary btn--icon commandbar__new"
            onClick={() => navigate("/accounting/journals/new")}
            aria-label={t("accounting.tabs.newEntry")}
          >
            +
          </button>
        </Tooltip>
        <UserMenu />
        <Tooltip label={t("shell.notifications")} placement="bottom">
          <button
            type="button"
            className="btn btn--ghost btn--icon"
            aria-label={t("shell.notifications")}
            onClick={() => navigate("/notifications")}
          >
            <NavIcon name="notifications" />
          </button>
        </Tooltip>
        <AppMenu />
      </div>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        einvoiceEnabled={einvoiceEnabled}
      />
    </header>
  );
}
