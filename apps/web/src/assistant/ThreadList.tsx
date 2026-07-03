import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  createConversation,
  deleteConversation,
  listConversations,
  updateConversation,
  type ConversationSummary,
} from "../api/assistant";
import { NavIcon } from "../app/icons";
import { useToast } from "../app/ToastContext";
import { Bdi } from "../components/Bdi";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { ListSkeleton } from "../components/ListSkeleton";
import { Tooltip } from "../components/Tooltip";
import { useAsync } from "../hooks/useAsync";
import { useListKeyboardNav } from "../hooks/useListKeyboardNav";
import i18n from "../i18n";
import { runOptimistic } from "../lib/optimistic";
import { useAssistant } from "./AssistantProvider";
import "./assistant-panel.css";

// A calm "3 hours ago" using the platform formatter — no dependency, respects the active language.
const RELATIVE_STEPS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 60 * 60 * 24 * 365],
  ["month", 60 * 60 * 24 * 30],
  ["week", 60 * 60 * 24 * 7],
  ["day", 60 * 60 * 24],
  ["hour", 60 * 60],
  ["minute", 60],
];

function relativeTime(iso: string, lang: string): string {
  const diff = (Date.parse(iso) - Date.now()) / 1000;
  const abs = Math.abs(diff);
  const fmt = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
  for (const [unit, secs] of RELATIVE_STEPS) {
    if (abs >= secs) return fmt.format(Math.round(diff / secs), unit);
  }
  return fmt.format(0, "second");
}

/**
 * The conversation history for the AI workspace — search, pinned/recent groups, an archived shelf,
 * and per-row rename/pin/archive/delete. Mounted in both surfaces (the fullscreen rail and the
 * panel's history view), reading one shared list keyed off the provider's refresh signal so both
 * stay in step. Row actions stay quiet until hover/focus (calm, low-noise); every mutation is
 * optimistic with a rollback toast, the same pattern the module lists use.
 *
 * `onPick` lets the floating/docked panel flip back to the conversation after a thread is chosen.
 */
export function ThreadList({ onPick }: { onPick?: () => void } = {}) {
  const { t } = useTranslation();
  const toast = useToast();
  const { conversationId, setConversationId, conversationsNonce, refreshConversations } = useAssistant();

  const [rawQuery, setRawQuery] = useState("");
  const [query, setQuery] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameText, setRenameText] = useState("");
  const [pendingDelete, setPendingDelete] = useState<ConversationSummary | null>(null);

  // Debounce the search so typing doesn't fire a request per keystroke.
  useEffect(() => {
    const id = window.setTimeout(() => setQuery(rawQuery.trim()), 250);
    return () => window.clearTimeout(id);
  }, [rawQuery]);

  // Only the default view (no search, not archived) is cached — search results never overwrite it.
  const cacheKey = !query && !showArchived ? "assistant:conversations" : undefined;
  const { data, loading, error, reload, mutate } = useAsync(
    () => listConversations(query || undefined, showArchived),
    [query, showArchived, conversationsNonce],
    cacheKey,
  );
  const items = useMemo(() => data ?? [], [data]);

  const pinned = useMemo(() => items.filter((c) => c.pinned), [items]);
  const rest = useMemo(() => items.filter((c) => !c.pinned), [items]);
  // Flat order for keyboard nav: pinned first, then the rest (matches the visual order).
  const ordered = useMemo(() => [...pinned, ...rest], [pinned, rest]);

  function select(c: ConversationSummary) {
    setConversationId(c.id);
    onPick?.();
  }

  const { active } = useListKeyboardNav<ConversationSummary>({
    items: ordered,
    onOpen: select,
    enabled: renamingId == null && pendingDelete == null,
  });

  function patchRow(c: ConversationSummary, patch: Partial<ConversationSummary>) {
    void runOptimistic<ConversationSummary[], ConversationSummary>({
      current: items,
      mutate,
      optimistic: (rows) => rows.map((r) => (r.id === c.id ? { ...r, ...patch } : r)),
      request: () => updateConversation(c.id, patch),
      settle: (predicted, updated) => predicted.map((r) => (r.id === updated.id ? updated : r)),
      toast,
      errorMessage: () => t("assistant.threads.saveFailed"),
    });
  }

  function commitRename(c: ConversationSummary) {
    const title = renameText.trim();
    setRenamingId(null);
    if (!title || title === c.title) return;
    patchRow(c, { title });
  }

  function confirmDelete() {
    const c = pendingDelete;
    setPendingDelete(null);
    if (!c) return;
    void runOptimistic<ConversationSummary[], void>({
      current: items,
      mutate,
      optimistic: (rows) => rows.filter((r) => r.id !== c.id),
      request: () => deleteConversation(c.id),
      toast,
      errorMessage: () => t("assistant.threads.saveFailed"),
    });
    // If the open conversation was deleted, clear the view.
    if (conversationId === c.id) setConversationId(null);
  }

  async function startNew() {
    try {
      const created = await createConversation();
      refreshConversations();
      select(created);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    }
  }

  const lang = i18n.resolvedLanguage || i18n.language || "ar";

  function renderRow(c: ConversationSummary, index: number) {
    const isRenaming = renamingId === c.id;
    return (
      <li
        key={c.id}
        className="thread-row"
        data-active={c.id === conversationId ? "" : undefined}
        data-kbd-active={index === active ? "true" : undefined}
        aria-selected={index === active}
      >
        {isRenaming ? (
          <input
            className="thread-row__rename"
            autoFocus
            dir="auto"
            value={renameText}
            onChange={(e) => setRenameText(e.target.value)}
            onBlur={() => commitRename(c)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                commitRename(c);
              } else if (e.key === "Escape") {
                e.preventDefault();
                setRenamingId(null);
              }
            }}
          />
        ) : (
          <button type="button" className="thread-row__main" onClick={() => select(c)}>
            <span className="thread-row__title">
              <Bdi>{c.title || t("assistant.threads.untitled")}</Bdi>
            </span>
            <span className="thread-row__meta">
              <span className="thread-row__time">{relativeTime(c.updated_at, lang)}</span>
              {c.preview && (
                <span className="thread-row__preview">
                  <Bdi>{c.preview}</Bdi>
                </span>
              )}
            </span>
          </button>
        )}

        {!isRenaming && (
          <div className="thread-row__actions" role="group" aria-label={c.title || t("assistant.threads.untitled")}>
            <Tooltip label={t("assistant.threads.rename")} placement="bottom">
              <button
                type="button"
                className="thread-row__action"
                aria-label={t("assistant.threads.rename")}
                onClick={() => {
                  setRenameText(c.title);
                  setRenamingId(c.id);
                }}
              >
                <NavIcon name="edit" />
              </button>
            </Tooltip>
            <Tooltip label={t(c.pinned ? "assistant.threads.unpin" : "assistant.threads.pin")} placement="bottom">
              <button
                type="button"
                className="thread-row__action"
                aria-label={t(c.pinned ? "assistant.threads.unpin" : "assistant.threads.pin")}
                aria-pressed={c.pinned}
                onClick={() => patchRow(c, { pinned: !c.pinned })}
              >
                <NavIcon name="pin" />
              </button>
            </Tooltip>
            <Tooltip
              label={t(c.archived ? "assistant.threads.unarchive" : "assistant.threads.archive")}
              placement="bottom"
            >
              <button
                type="button"
                className="thread-row__action"
                aria-label={t(c.archived ? "assistant.threads.unarchive" : "assistant.threads.archive")}
                onClick={() => patchRow(c, { archived: !c.archived })}
              >
                <NavIcon name={c.archived ? "rotate" : "archive"} />
              </button>
            </Tooltip>
            <Tooltip label={t("assistant.threads.delete")} placement="bottom">
              <button
                type="button"
                className="thread-row__action thread-row__action--danger"
                aria-label={t("assistant.threads.delete")}
                onClick={() => setPendingDelete(c)}
              >
                <NavIcon name="trash" />
              </button>
            </Tooltip>
          </div>
        )}
      </li>
    );
  }

  return (
    <div className="thread-list">
      <div className="thread-list__head">
        <div className="thread-list__search">
          <NavIcon name="search" />
          <input
            type="search"
            dir="auto"
            className="thread-list__search-input"
            placeholder={t("assistant.threads.search")}
            value={rawQuery}
            onChange={(e) => setRawQuery(e.target.value)}
          />
        </div>
        <Tooltip label={t("assistant.threads.new")} placement="bottom">
          <button
            type="button"
            className="thread-list__new"
            aria-label={t("assistant.threads.new")}
            onClick={() => void startNew()}
          >
            <NavIcon name="plus" />
          </button>
        </Tooltip>
      </div>

      <div className="thread-list__body">
        {loading ? (
          <ListSkeleton rows={5} title={false} />
        ) : error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : ordered.length === 0 ? (
          query ? (
            <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
          ) : (
            <EmptyState title={t("assistant.threads.empty")} hint={t("assistant.threads.emptyHint")} />
          )
        ) : (
          <>
            {pinned.length > 0 && (
              <ul className="thread-list__group">{pinned.map((c, i) => renderRow(c, i))}</ul>
            )}
            <ul className="thread-list__group">{rest.map((c, i) => renderRow(c, pinned.length + i))}</ul>
          </>
        )}
      </div>

      <button
        type="button"
        className="thread-list__archived-toggle"
        onClick={() => setShowArchived((v) => !v)}
        aria-pressed={showArchived}
      >
        <NavIcon name="archive" />
        {t(showArchived ? "assistant.threads.hideArchived" : "assistant.threads.showArchived")}
      </button>

      <ConfirmDialog
        open={pendingDelete != null}
        danger
        title={t("assistant.threads.delete")}
        body={t("assistant.threads.deleteConfirm")}
        confirmLabel={t("assistant.threads.delete")}
        onConfirm={confirmDelete}
        onClose={() => setPendingDelete(null)}
      />
    </div>
  );
}
