import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import type { InboxItem } from "../api/notifications";
import { relativeTime } from "../lib/relativeTime";
import { EmptyState } from "../components/EmptyState";
import { Tooltip } from "../components/Tooltip";
import { NavIcon } from "./icons";
import "./inbox.css";

// Each source event maps to (a) a localised headline/body key and (b) where clicking it lands. Kept
// as a small table so new in-app sources add one row here, not a branch. Unknown events fall back to
// the row's stored subject/body and don't navigate.
const EVENT: Record<string, { key: string; route: string | null }> = {
  "crm.TicketEscalated": { key: "ticketEscalated", route: "/crm/tickets" },
};

interface InboxPanelProps {
  open: boolean;
  onClose: () => void;
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
 * beneath. Esc closes and focus returns to the bell (mirrors the assistant panel).
 */
export function InboxPanel({
  open,
  onClose,
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

  return (
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
              const headline = meta
                ? t(`inbox.events.${meta.key}.title`, { ref: item.reference })
                : item.subject;
              const detail = meta
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
    </aside>
  );
}
