import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { usePreferences } from "../preferences/PreferencesContext";
import { useGlobalShortcuts } from "../hooks/useGlobalShortcuts";
import { useInbox } from "../hooks/useInbox";
import { useAssistant } from "../assistant/AssistantProvider";
import { Tooltip } from "../components/Tooltip";
import { AppMenu } from "./AppMenu";
import { CommandPalette } from "./CommandPalette";
import { InboxPanel } from "./InboxPanel";
import { useShortcuts } from "./ShortcutsContext";
import { UserMenu } from "./UserMenu";
import { NavIcon } from "./icons";
import "./CommandBar.css";

export function CommandBar({ onMenu }: { onMenu?: () => void }) {
  const { t } = useTranslation();
  const { prefs } = usePreferences();
  const { openShortcuts } = useShortcuts();
  const { enabled: assistantEnabled, toggle: toggleAssistant } = useAssistant();
  const navigate = useNavigate();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [inboxOpen, setInboxOpen] = useState(false);
  const bellRef = useRef<HTMLButtonElement>(null);
  const inbox = useInbox();

  // When e-invoicing is turned off in setup, hide it from every nav surface (sidebar, palette,
  // cheat-sheet and the g-key chord) so "disabled" reads consistently.
  const einvoiceEnabled = prefs?.einvoice_enabled !== false;

  // App-wide keyboard layer: ⌘K / `/` / `c` open the palette, `g`+key navigates,
  // `?` opens the cheat-sheet (mounted in the shell). Stable callback so the listener isn't re-bound.
  const openPalette = useCallback(() => setPaletteOpen(true), []);
  useGlobalShortcuts({
    openPalette,
    openShortcuts,
    einvoiceEnabled,
    // ⌘J is inert while the assistant is off/unknown (the feature is hidden everywhere).
    toggleAssistant: assistantEnabled ? toggleAssistant : undefined,
  });

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
        <span className="commandbar__search-icon" aria-hidden="true"><NavIcon name="search" /></span>
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
        {assistantEnabled && (
          <Tooltip label={t("assistant.open")} placement="bottom" shortcut={["⌘", "J"]}>
            <button
              type="button"
              className="btn btn--ghost btn--icon"
              aria-label={t("assistant.open")}
              onClick={toggleAssistant}
            >
              <NavIcon name="sparkle" />
            </button>
          </Tooltip>
        )}
        <UserMenu />
        <Tooltip label={t("inbox.title")} placement="bottom">
          <button
            ref={bellRef}
            type="button"
            className="btn btn--ghost btn--icon commandbar__bell"
            aria-label={t("inbox.title")}
            aria-haspopup="dialog"
            aria-expanded={inboxOpen}
            data-unread={inbox.unread ? "true" : undefined}
            onClick={() => setInboxOpen((v) => !v)}
          >
            <NavIcon name="notifications" />
            {inbox.unread && <span className="commandbar__bell-dot" aria-hidden="true" />}
          </button>
        </Tooltip>
        <AppMenu />
      </div>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        einvoiceEnabled={einvoiceEnabled}
      />
      <InboxPanel
        open={inboxOpen}
        onClose={() => setInboxOpen(false)}
        anchorRef={bellRef}
        items={inbox.items}
        loading={inbox.loading}
        error={inbox.error}
        onReload={inbox.reload}
        onMarkRead={inbox.markRead}
        onMarkAll={inbox.markAll}
      />
    </header>
  );
}
