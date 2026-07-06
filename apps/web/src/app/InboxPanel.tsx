import { useEffect, useRef, useState, type RefObject } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import type { InboxItem } from "../api/notifications";
import { relativeTime } from "../lib/relativeTime";
import { EmptyState } from "../components/EmptyState";
import { Tooltip } from "../components/Tooltip";
import { NavIcon } from "./icons";
import "./inbox.css";

// Each source event maps to (a) an optional localised headline/body key and (b) where clicking it
// lands. Kept as a small table so new in-app sources add one row here, not a branch. Without a `key`
// the row shows its own stored subject/body (used for events whose text is already composed, like the
// morning digest); without a `route` the row marks read but doesn't navigate.
const EVENT: Record<string, { key?: string; route: string | null }> = {
  "crm.TicketEscalated": { key: "ticketEscalated", route: "/crm/tickets" },
  // The digest's Arabic/English text is pre-composed; clicking it opens the dashboard, whose
  // "needs attention today" panel is the same at-a-glance view the digest summarises.
  "assistant.MorningDigest": { route: "/" },
};

interface InboxPanelProps {
  open: boolean;
  onClose: () => void;
  /** The bell button this panel drops from — clicks outside both stay open, everywhere else closes it. */
  anchorRef: RefObject<HTMLElement | null>;
  items: InboxItem[];
  loading: boolean;
  error: string | null;
  onReload: () => void;
  onMarkRead: (id: string) => void;
  onMarkAll: () => void;
}

/**
 * The notifications inbox — a floating panel from the command-bar bell. Rows are calm: a headline, a
 * one-line body, the source module word and a relative time; unread reads as a heavier weight + a
 * quiet inline-start marker, never a colour or a count. Clicking a row opens its record and marks it
 * read. j/k move a highlight, Enter opens it — all scoped to the panel so it never fights the list
 * beneath. Esc or a click outside closes it and focus returns to the bell.
 */
export function InboxPanel({
  open,
  onClose,
  anchorRef,
  items,
  loading,
  error,
  onReload,
  onMarkRead,
  onMarkAll,
}: InboxPanelProps) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const panelRef = useRef<HTMLElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const [active, setActive] = useState(-1);
  const lang = i18n.resolvedLanguage || i18n.language || "ar";

  // Refresh on each open so the list is current, and reset the highlight.
  useEffect(() => {
    if (!open) return;
    onReload();
    setActive(-1);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  // Esc closes; on open focus moves into the panel and returns to the trigger on close.
  useEffect(() => {
    if (!open) return;
    returnFocus.current = document.activeElement as HTMLElement | null;
    const raf = window.requestAnimationFrame(() => panelRef.current?.focus());
    return () => {
      window.cancelAnimationFrame(raf);
      returnFocus.current?.focus?.();
    };
  }, [open]);

  // A click anywhere outside the panel and its bell also closes it (Linear-style), same idiom as
  // the shared Popover.
  useEffect(() => {
    if (!open) return;
    function onPointer(e: PointerEvent) {
      const target = e.target as Node;
      if (panelRef.current?.contains(target) || anchorRef.current?.contains(target)) return;
      onClose();
    }
    document.addEventListener("pointerdown", onPointer, true);
    return () => document.removeEventListener("pointerdown", onPointer, true);
  }, [open, onClose, anchorRef]);

  if (!open) return null;

  function openItem(item: InboxItem) {
    onMarkRead(item.id);
    const route = EVENT[item.event_name]?.route ?? null;
    onClose();
    if (route) navigate(route);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    } else if (e.key === "j" || e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (items.length === 0 ? -1 : Math.min(i + 1, items.length - 1)));
    } else if (e.key === "k" || e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i <= 0 ? 0 : i - 1));
    } else if (e.key === "Enter" || e.key === "o") {
      const item = active >= 0 ? items[active] : undefined;
      if (item) {
        e.preventDefault();
        openItem(item);
      }
    }
  }

  const hasUnread = items.some((n) => n.read_at === null);

  // Portalled to <body> so it isn't trapped in the command bar's stacking context (position:sticky
  // z-index:5) — otherwise the sticky page header bar (z-index:15) would render over it. The panel is
  // position:fixed with corner insets, so moving it out of the bar's DOM doesn't change where it sits.
  return createPortal(
    <aside
      ref={panelRef}
      className="inbox-panel"
      role="dialog"
      aria-label={t("inbox.title")}
      tabIndex={-1}
      onKeyDown={onKeyDown}
    >
      <header className="inbox-panel__head">
        <span className="inbox-panel__title">
          <span className="inbox-panel__title-icon" aria-hidden="true">
            <NavIcon name="notifications" />
          </span>
          {t("inbox.title")}
        </span>
        <div className="inbox-panel__tools">
          {hasUnread && (
            <button type="button" className="inbox-panel__markall" onClick={onMarkAll}>
              {t("inbox.markAllRead")}
            </button>
          )}
          <Tooltip label={t("inbox.close")} placement="bottom">
            <button
              type="button"
              className="inbox-panel__tool"
              aria-label={t("inbox.close")}
              onClick={onClose}
            >
              <NavIcon name="close" />
            </button>
          </Tooltip>
        </div>
      </header>

      <div className="inbox-panel__body">
        {loading && items.length === 0 && (
          <p className="inbox-panel__loading" dir="auto">
            {t("common.loading")}
          </p>
        )}
        {error && (
          <p className="inbox-panel__error" dir="auto">
            {error}
          </p>
        )}
        {!loading && !error && items.length === 0 && (
          <EmptyState title={t("inbox.empty")} hint={t("inbox.emptyHint")} />
        )}

        {items.length > 0 && (
          <ul className="inbox-list">
            {items.map((item, i) => {
              const meta = EVENT[item.event_name];
              // Templated events render from their i18n key; everything else (incl. the pre-composed
              // digest) shows its own stored subject/body.
              const headline = meta?.key
                ? t(`inbox.events.${meta.key}.title`, { ref: item.reference })
                : item.subject;
              const detail = meta?.key
                ? t(`inbox.events.${meta.key}.body`, { ref: item.reference })
                : item.body;
              const unread = item.read_at === null;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className={`inbox-row${unread ? " inbox-row--unread" : ""}`}
                    data-kbd-active={i === active ? "true" : undefined}
                    aria-selected={i === active}
                    onClick={() => openItem(item)}
                  >
                    <span className="inbox-row__dot" aria-hidden="true" />
                    <span className="inbox-row__main">
                      <span className="inbox-row__headline" dir="auto">
                        {headline}
                      </span>
                      <span className="inbox-row__body" dir="auto">
                        {detail}
                      </span>
                      <span className="inbox-row__meta">
                        <span className="inbox-row__module">
                          {t(`nav.${item.event_name.split(".")[0]}`, {
                            defaultValue: item.event_name.split(".")[0],
                          })}
                        </span>
                        <span className="inbox-row__time latin">
                          {relativeTime(item.created_at, lang)}
                        </span>
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>,
    document.body,
  );
}
