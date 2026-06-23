import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { normalizeSearch } from "../lib/arabicSearch";
import "./CommandPalette.css";

type Group = "create" | "go";

interface Command {
  id: string;
  label: string;
  to: string;
  group: Group;
}

/**
 * ⌘K command palette: a single keyboard-first entry point to jump to any page or
 * start the common "create" actions. Built on the native <dialog> top layer, so it
 * escapes the app-shell stacking context and gets modal focus-trapping + Esc for
 * free. Direction-agnostic (logical CSS) and bilingual — it filters on the
 * translated label, so it matches whatever language the user is reading.
 */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);

  const commands = useMemo<Command[]>(
    () => [
      // Create — the common "new document" actions.
      { id: "new-order", label: t("command.newOrder"), to: "/sales/orders/new", group: "create" },
      { id: "new-quotation", label: t("command.newQuotation"), to: "/sales/quotations/new", group: "create" },
      { id: "new-po", label: t("command.newPurchaseOrder"), to: "/purchasing/orders/new", group: "create" },
      { id: "new-pr", label: t("command.newPurchaseRequest"), to: "/purchasing/requests/new", group: "create" },
      { id: "new-journal", label: t("command.newJournal"), to: "/accounting/journals/new", group: "create" },
      { id: "new-workflow", label: t("command.newWorkflow"), to: "/workflows/new", group: "create" },
      // Go to — modules and the most-visited reports.
      { id: "go-dashboard", label: t("nav.dashboard"), to: "/", group: "go" },
      { id: "go-sales", label: t("nav.sales"), to: "/sales", group: "go" },
      { id: "go-purchasing", label: t("nav.purchasing"), to: "/purchasing", group: "go" },
      { id: "go-inventory", label: t("nav.inventory"), to: "/inventory", group: "go" },
      { id: "go-accounting", label: t("nav.accounting"), to: "/accounting", group: "go" },
      { id: "go-einvoice", label: t("nav.einvoice"), to: "/einvoice", group: "go" },
      { id: "go-crm", label: t("nav.crm"), to: "/crm", group: "go" },
      { id: "go-notifications", label: t("nav.notifications"), to: "/notifications", group: "go" },
      { id: "go-workflows", label: t("nav.workflows"), to: "/workflows", group: "go" },
      { id: "go-settings", label: t("settings.title"), to: "/settings", group: "go" },
      { id: "go-customers", label: t("command.customers"), to: "/sales/customers", group: "go" },
      { id: "go-suppliers", label: t("command.suppliers"), to: "/purchasing/suppliers", group: "go" },
      { id: "go-stock", label: t("command.stockOnHand"), to: "/inventory/stock-on-hand", group: "go" },
      { id: "go-trial-balance", label: t("command.trialBalance"), to: "/accounting/trial-balance", group: "go" },
      { id: "go-general-ledger", label: t("command.generalLedger"), to: "/accounting/general-ledger", group: "go" },
      { id: "go-income", label: t("command.incomeStatement"), to: "/accounting/income-statement", group: "go" },
      { id: "go-balance", label: t("command.balanceSheet"), to: "/accounting/balance-sheet", group: "go" },
    ],
    [t],
  );

  const filtered = useMemo(() => {
    const q = normalizeSearch(query.trim());
    if (!q) return commands;
    return commands.filter((c) => normalizeSearch(c.label).includes(q));
  }, [commands, query]);

  // Keep the native dialog's open state in sync with the controlled `open` prop,
  // resetting the query and focusing the input each time it opens.
  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    if (open && !dlg.open) {
      setQuery("");
      setActive(0);
      dlg.showModal();
      requestAnimationFrame(() => inputRef.current?.focus());
    } else if (!open && dlg.open) {
      dlg.close();
    }
  }, [open]);

  // Clamp the highlighted row whenever the result set shrinks.
  useEffect(() => {
    setActive((i) => Math.min(i, Math.max(filtered.length - 1, 0)));
  }, [filtered.length]);

  function run(cmd: Command | undefined) {
    if (!cmd) return;
    onClose();
    navigate(cmd.to);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      run(filtered[active]);
    }
  }

  // The full-viewport dialog is the click-away surface; the card sits inside it.
  function onBackdropClick(e: React.MouseEvent) {
    if (e.target === dialogRef.current) onClose();
  }

  const labelFor = (g: Group) => (g === "create" ? t("command.groupCreate") : t("command.groupGo"));
  const groups: Group[] = ["create", "go"];

  return (
    <dialog
      ref={dialogRef}
      className="cmdp"
      aria-label={t("command.placeholder")}
      onClose={onClose}
      onCancel={onClose}
      onClick={onBackdropClick}
    >
      <div className="cmdp__panel">
        <div className="cmdp__search">
          <span className="cmdp__search-icon" aria-hidden="true">⌕</span>
          <input
            ref={inputRef}
            type="text"
            className="cmdp__input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={t("command.placeholder")}
            role="combobox"
            aria-expanded="true"
            aria-controls="cmdp-list"
            aria-autocomplete="list"
          />
        </div>

        <div className="cmdp__results" id="cmdp-list" role="listbox">
          {filtered.length === 0 && (
            <p className="cmdp__empty">
              {t("command.empty")} “{query.trim()}”
            </p>
          )}
          {groups.map((g) => {
            const rows = filtered.filter((c) => c.group === g);
            if (rows.length === 0) return null;
            return (
              <div className="cmdp__group" key={g}>
                <p className="cmdp__group-label">{labelFor(g)}</p>
                <ul className="cmdp__list">
                  {rows.map((cmd) => {
                    const idx = filtered.indexOf(cmd);
                    return (
                      <li key={cmd.id}>
                        <button
                          type="button"
                          role="option"
                          aria-selected={idx === active}
                          className={
                            idx === active ? "cmdp__item cmdp__item--active" : "cmdp__item"
                          }
                          onMouseMove={() => setActive(idx)}
                          onClick={() => run(cmd)}
                        >
                          <span>{cmd.label}</span>
                          <span className="cmdp__item-go" aria-hidden="true">↵</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>

        <footer className="cmdp__foot">
          <span><kbd className="cmdp__kbd latin">↑</kbd><kbd className="cmdp__kbd latin">↓</kbd> {t("command.hintMove")}</span>
          <span><kbd className="cmdp__kbd latin">↵</kbd> {t("command.hintOpen")}</span>
          <span><kbd className="cmdp__kbd latin">Esc</kbd> {t("command.hintClose")}</span>
        </footer>
      </div>
    </dialog>
  );
}
