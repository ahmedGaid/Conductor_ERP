import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { useHelp } from "../help/HelpContext";
import { Popover } from "../components/Popover";
import { Tooltip } from "../components/Tooltip";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { ThemeToggle } from "./ThemeToggle";
import { useShortcuts } from "./ShortcutsContext";
import "./AppMenu.css";

/**
 * The product "⋮" menu in the top bar (trailing edge of the command bar). Collects the product-level
 * controls that shape how the app looks and behaves: theme, language, the keyboard cheat-sheet and
 * help. Personal actions live in the adjacent user menu; workspace actions live on the company chip
 * at the foot of the sidebar — not here.
 */
export function AppMenu() {
  const { t } = useTranslation();
  const { openHelp } = useHelp();
  const { openShortcuts } = useShortcuts();
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);

  const act = (fn: () => void) => {
    setOpen(false);
    fn();
  };

  return (
    <>
      <Tooltip label={t("shell.menu")} placement="bottom">
        <button
          ref={triggerRef}
          type="button"
          className="btn btn--ghost btn--icon"
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-label={t("shell.menu")}
          onClick={() => setOpen((o) => !o)}
        >
          <span aria-hidden="true">⋮</span>
        </button>
      </Tooltip>

      <Popover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={triggerRef}
        className="appmenu"
        ariaLabel={t("shell.menu")}
      >
        {/* Set-once preferences — toggling stays in the menu so the effect is visible. */}
        <div className="appmenu__pref">
          <span>{t("settings.appearance.theme")}</span>
          <ThemeToggle />
        </div>
        <div className="appmenu__pref">
          <span>{t("language.label")}</span>
          <LanguageSwitcher />
        </div>

        <div className="appmenu__sep" role="separator" />

        <button className="appmenu__item" type="button" onClick={() => act(openShortcuts)}>
          <span>{t("shortcuts.title")}</span>
          <kbd className="appmenu__kbd latin">?</kbd>
        </button>
        <button className="appmenu__item" type="button" onClick={() => act(openHelp)}>
          {t("shell.help")}
        </button>
      </Popover>
    </>
  );
}
