import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { searchEntities } from "../api/core";
import { useAssistant } from "../assistant/AssistantProvider";
import { JOURNEYS } from "../help/content/journeys";
import type { L } from "../help/types";
import { normalizeSearch } from "../lib/arabicSearch";
import { getRecents, recordRecent } from "../lib/recents";
import { usePaletteActionList } from "./PaletteActionsContext";
import { NavIcon } from "./icons";
import "./CommandPalette.css";

type Group = "page" | "results" | "recent" | "create" | "go" | "help" | "ask";

interface Command {
  id: string;
  label: string;
  group: Group;
  /** Navigation target. Mutually exclusive with `run` (page actions run a callback instead). */
  to?: string;
  /** Contextual page action — invoked instead of navigating. */
  run?: () => void;
  sublabel?: string; // secondary line (record code/number + localized type), live results only
}

/**
 * ⌘K command palette: a single keyboard-first entry point to jump to any page or
 * start the common "create" actions. Built on the native <dialog> top layer, so it
 * escapes the app-shell stacking context and gets modal focus-trapping + Esc for
 * free. Direction-agnostic (logical CSS) and bilingual — it filters on the
 * translated label, so it matches whatever language the user is reading.
 */
export function CommandPalette({
  open,
  onClose,
  einvoiceEnabled = true,
}: {
  open: boolean;
  onClose: () => void;
  einvoiceEnabled?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const lang: keyof L = i18n.language?.startsWith("ar") ? "ar" : "en";
  const navigate = useNavigate();
  const location = useLocation();
  const { enabled: assistantEnabled, openPanelWithMessage } = useAssistant();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const activeItemRef = useRef<HTMLButtonElement>(null);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  // Live entity hits (customers, items, orders…) from the server, Arabic-tolerant. Static page
  // commands below still match instantly client-side; these add records to the same list.
  const [results, setResults] = useState<Command[]>([]);
  const searchSeq = useRef(0);

  const commands = useMemo<Command[]>(
    () => ([
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
      { id: "go-imports", label: t("nav.imports"), to: "/imports", group: "go" },
      { id: "go-settings", label: t("settings.title"), to: "/settings", group: "go" },
      { id: "go-customers", label: t("command.customers"), to: "/sales/customers", group: "go" },
      { id: "go-suppliers", label: t("command.suppliers"), to: "/purchasing/suppliers", group: "go" },
      { id: "go-stock", label: t("command.stockOnHand"), to: "/inventory/stock-on-hand", group: "go" },
      { id: "go-trial-balance", label: t("command.trialBalance"), to: "/accounting/trial-balance", group: "go" },
      { id: "go-general-ledger", label: t("command.generalLedger"), to: "/accounting/general-ledger", group: "go" },
      { id: "go-income", label: t("command.incomeStatement"), to: "/accounting/income-statement", group: "go" },
      { id: "go-balance", label: t("command.balanceSheet"), to: "/accounting/balance-sheet", group: "go" },
      // User Guide journeys — deep-link straight to the matching page of the standalone guide
      // (FILE_15 Task C: ⌘K is one of the guide's three reachability roads).
      ...JOURNEYS.map((j) => ({
        id: `help-journey-${j.id}`,
        label: t("command.helpJourney", { title: j.title[lang] }),
        to: `/help/guide/${j.id}`,
        group: "help" as const,
      })),
    ] as Command[]).filter((cmd) => einvoiceEnabled || cmd.id !== "go-einvoice"),
    [t, einvoiceEnabled, lang],
  );

  // Contextual actions the current page has registered ("Approve", "Confirm", …), surfaced as a
  // "This page" group at the very top. They run a callback rather than navigating.
  const pageActionList = usePaletteActionList();
  const pageActions = useMemo<Command[]>(
    () => pageActionList.map((a) => ({ id: `page:${a.id}`, label: a.label, group: "page", run: a.run })),
    [pageActionList],
  );

  // Track every visited page so the palette can offer a "jump back" list. The palette is always
  // mounted in the shell, so this effect sees all route changes.
  useEffect(() => {
    recordRecent(location.pathname);
  }, [location.pathname]);

  // Live entity search: debounce the query, then ask the server for matching records. A monotonic
  // sequence guards against out-of-order responses, and the closed/empty states clear the list.
  useEffect(() => {
    const q = query.trim();
    if (!open || q.length < 2) {
      setResults([]);
      return;
    }
    const seq = ++searchSeq.current;
    const timer = setTimeout(() => {
      searchEntities(q)
        .then((hits) => {
          if (seq !== searchSeq.current) return; // a newer keystroke already fired
          setResults(
            hits.map((h, i) => ({
              id: `hit-${h.type}-${i}`,
              label: h.label,
              to: h.to,
              group: "results" as const,
              sublabel: [h.sublabel, t(`command.type.${h.type}`)].filter(Boolean).join(" · "),
            })),
          );
        })
        .catch(() => {
          if (seq === searchSeq.current) setResults([]);
        });
    }, 200);
    return () => clearTimeout(timer);
  }, [query, open, t]);

  // Recently-visited destinations, newest first — module/list pages resolve their label from the
  // command list; specific entities (an order, an opportunity) carry their own stored label and
  // become a synthetic go-to command. Deduped and capped. Recomputed when the palette opens (fresh
  // localStorage) and hidden once you type.
  const recent = useMemo<Command[]>(() => {
    if (!open || query.trim()) return [];
    const out: Command[] = [];
    const seen = new Set<string>();
    for (const { path, label } of getRecents()) {
      const known = commands.find((c) => c.to === path);
      const cmd: Command | undefined = known
        ? known
        : label
          ? { id: `recent:${path}`, label, to: path, group: "recent" }
          : undefined;
      if (cmd && !seen.has(cmd.id)) {
        seen.add(cmd.id);
        out.push(cmd);
        if (out.length >= 5) break;
      }
    }
    return out;
  }, [commands, query, open]);

  // The flat, ordered result list that drives arrow-key navigation. Empty query: page actions, then
  // recents, then the full set with recents removed. While typing: page actions + commands whose
  // label matches (recents are just shortcuts to the same destinations, so they're dropped).
  const visible = useMemo(() => {
    const q = normalizeSearch(query.trim());
    // Typing: matching page actions, then server record hits, then the static commands that match.
    if (q)
      return [
        ...pageActions.filter((c) => normalizeSearch(c.label).includes(q)),
        ...results,
        ...commands.filter((c) => normalizeSearch(c.label).includes(q)),
      ];
    const recentIds = new Set(recent.map((c) => c.id));
    return [...pageActions, ...recent, ...commands.filter((c) => !recentIds.has(c.id))];
  }, [commands, pageActions, query, recent, results]);

  // The AI fallthrough row: appended last, never ahead of a real match. Offered when the query
  // reads like a question (no match at all, more than a few words, or ends with ؟/?) — the same
  // heuristic whether the user is typing Arabic or English.
  const askAi = useMemo<Command | null>(() => {
    if (!assistantEnabled) return null;
    const q = query.trim();
    if (!q) return null;
    const wordCount = q.split(/\s+/).filter(Boolean).length;
    const looksLikeQuestion = visible.length === 0 || wordCount > 3 || /[؟?]$/.test(q);
    if (!looksLikeQuestion) return null;
    return {
      id: "ask-ai",
      label: t("commandBar.askAi", { query: q }),
      group: "ask",
      run: () => openPanelWithMessage(q),
    };
  }, [assistantEnabled, query, visible, t, openPanelWithMessage]);

  const flat = useMemo(() => (askAi ? [...visible, askAi] : visible), [visible, askAi]);

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
    setActive((i) => Math.min(i, Math.max(flat.length - 1, 0)));
  }, [flat.length]);

  // Keep the highlighted row in view while arrowing through a long list.
  useEffect(() => {
    activeItemRef.current?.scrollIntoView({ block: "nearest" });
  }, [active]);

  function run(cmd: Command | undefined) {
    if (!cmd) return;
    onClose();
    if (cmd.run) cmd.run();
    else if (cmd.to) navigate(cmd.to);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, flat.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      run(flat[active]);
    }
  }

  // The full-viewport dialog is the click-away surface; the card sits inside it.
  function onBackdropClick(e: React.MouseEvent) {
    if (e.target === dialogRef.current) onClose();
  }

  const labelFor = (g: Group) =>
    g === "page"
      ? t("command.groupPage")
      : g === "results"
      ? t("command.groupResults")
      : g === "recent"
        ? t("command.groupRecent")
        : g === "create"
          ? t("command.groupCreate")
          : g === "go"
            ? t("command.groupGo")
            : g === "help"
              ? t("command.groupHelp")
              : null; // "ask" renders as a bare final row, no group header

  // Render order: page actions, live results, recents, create, go, then the AI fallthrough —
  // matching the `flat` sequence so arrow-key navigation flows top-to-bottom across the groups.
  const recentIds = new Set(recent.map((c) => c.id));
  const allSections: { key: Group; rows: Command[] }[] = [
    { key: "page", rows: visible.filter((c) => c.group === "page") },
    { key: "results", rows: visible.filter((c) => c.group === "results") },
    { key: "recent", rows: recent },
    { key: "create", rows: visible.filter((c) => c.group === "create" && !recentIds.has(c.id)) },
    { key: "go", rows: visible.filter((c) => c.group === "go" && !recentIds.has(c.id)) },
    { key: "help", rows: visible.filter((c) => c.group === "help") },
    { key: "ask", rows: askAi ? [askAi] : [] },
  ];
  const sections = allSections.filter((s) => s.rows.length > 0);

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
          <span className="cmdp__search-icon" aria-hidden="true"><NavIcon name="search" /></span>
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
          {flat.length === 0 && (
            <p className="cmdp__empty">
              {t("command.empty")} “{query.trim()}”
            </p>
          )}
          {sections.map((section) => {
            const label = labelFor(section.key);
            return (
              <div className="cmdp__group" key={section.key}>
                {label && <p className="cmdp__group-label">{label}</p>}
                <ul className="cmdp__list">
                  {section.rows.map((cmd) => {
                    const idx = flat.indexOf(cmd);
                    return (
                      <li key={cmd.id}>
                        <button
                          ref={idx === active ? activeItemRef : undefined}
                          type="button"
                          role="option"
                          aria-selected={idx === active}
                          className={
                            idx === active ? "cmdp__item cmdp__item--active" : "cmdp__item"
                          }
                          onMouseMove={() => setActive(idx)}
                          onClick={() => run(cmd)}
                        >
                          {cmd.group === "ask" && (
                            <span className="cmdp__item-icon" aria-hidden="true">
                              <NavIcon name="sparkle" />
                            </span>
                          )}
                          <span className="cmdp__item-text">
                            <span className="cmdp__item-label">{cmd.label}</span>
                            {cmd.sublabel && <span className="cmdp__item-sub">{cmd.sublabel}</span>}
                          </span>
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
