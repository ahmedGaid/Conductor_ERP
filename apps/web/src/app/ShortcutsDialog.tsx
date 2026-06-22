import { Fragment, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import "./CommandPalette.css";
import "./ShortcutsDialog.css";

interface Shortcut {
  keys: string[];
  label: string;
}

/**
 * The `?` cheat-sheet — a read-only reference for the app-wide keyboard layer.
 * Shares the command palette's native-<dialog> shell (top layer, focus trap, Esc)
 * and the same kbd styling, so the two feel like one keyboard system.
 */
export function ShortcutsDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    if (open && !dlg.open) dlg.showModal();
    else if (!open && dlg.open) dlg.close();
  }, [open]);

  const general: Shortcut[] = [
    { keys: ["⌘", "K"], label: t("shortcuts.palette") },
    { keys: ["/"], label: t("shortcuts.search") },
    { keys: ["C"], label: t("shortcuts.create") },
    { keys: ["?"], label: t("shortcuts.help") },
  ];
  const navigation: Shortcut[] = [
    { keys: ["G", "D"], label: t("nav.dashboard") },
    { keys: ["G", "S"], label: t("nav.sales") },
    { keys: ["G", "P"], label: t("nav.purchasing") },
    { keys: ["G", "I"], label: t("nav.inventory") },
    { keys: ["G", "A"], label: t("nav.accounting") },
    { keys: ["G", "E"], label: t("nav.einvoice") },
    { keys: ["G", "C"], label: t("nav.crm") },
    { keys: ["G", "N"], label: t("nav.notifications") },
    { keys: ["G", "W"], label: t("nav.workflows") },
    { keys: ["G", ","], label: t("settings.title") },
  ];

  // The full-viewport dialog is the click-away surface; the card sits inside it.
  function onBackdropClick(e: React.MouseEvent) {
    if (e.target === dialogRef.current) onClose();
  }

  return (
    <dialog
      ref={dialogRef}
      className="cmdp"
      aria-label={t("shortcuts.title")}
      onClose={onClose}
      onCancel={onClose}
      onClick={onBackdropClick}
    >
      <div className="cmdp__panel shortcuts">
        <header className="shortcuts__head">
          <h2 className="shortcuts__title">{t("shortcuts.title")}</h2>
        </header>

        <div className="shortcuts__body">
          <section className="shortcuts__section">
            <p className="cmdp__group-label">{t("shortcuts.general")}</p>
            <ul className="shortcuts__list">
              {general.map((s) => (
                <ShortcutRow key={s.label} keys={s.keys} label={s.label} />
              ))}
            </ul>
          </section>
          <section className="shortcuts__section">
            <p className="cmdp__group-label">{t("shortcuts.navigation")}</p>
            <ul className="shortcuts__list">
              {navigation.map((s) => (
                <ShortcutRow key={s.label} keys={s.keys} label={s.label} />
              ))}
            </ul>
          </section>
        </div>

        <footer className="cmdp__foot">
          <span><kbd className="cmdp__kbd latin">Esc</kbd> {t("command.hintClose")}</span>
        </footer>
      </div>
    </dialog>
  );
}

function ShortcutRow({ keys, label }: Shortcut) {
  const { t } = useTranslation();
  return (
    <li className="shortcuts__row">
      <span className="shortcuts__label">{label}</span>
      <span className="shortcuts__keys">
        {keys.map((k, i) => (
          <Fragment key={i}>
            {i > 0 && <span className="shortcuts__then">{t("shortcuts.then")}</span>}
            <kbd className="cmdp__kbd latin">{k}</kbd>
          </Fragment>
        ))}
      </span>
    </li>
  );
}
