import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";

import { getRecordTimeline, type TimelineEntry } from "../api/audit";
import { NavIcon } from "../app/icons";
import { formatMinor } from "../lib/money";
import { relativeTime } from "../lib/relativeTime";
import { Bdi } from "./Bdi";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { ListSkeleton } from "./ListSkeleton";
import { Tooltip } from "./Tooltip";
import "./recordTimeline.css";

const PAGE_SIZE = 20;

// snake_case action codes fall back to a readable phrase when no i18n key covers them yet (the
// audit trail spans every module, so the dictionary only needs to grow where it reads oddly).
function humanize(code: string): string {
  return code.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

function formatValue(field: string, value: unknown, t: TFunction): string {
  if (value === null || value === undefined || value === "") return t("timeline.emptyValue");
  if (typeof value === "number" && field.endsWith("_minor")) return formatMinor(value);
  if (typeof value === "boolean") return value ? t("common.yes") : t("common.no");
  return String(value);
}

/**
 * Quiet, newest-first activity feed for one record — who did what, when, and (for an update) which
 * fields changed. Every audit entry only ever stores a full snapshot (never a partial diff), so the
 * "old -> new" chips come from the backend comparing consecutive snapshots (`erp/audit/history.py`).
 * A change caused by the AI assistant or a data import carries a small source glyph, so a disputed
 * number or action stays click-traceable back to what actually wrote it (STRATEGY mechanic 4).
 * Blame-free tone throughout — the timeline states facts, never fault.
 */
export function RecordTimeline({ entityType, entityId }: { entityType: string; entityId: string }) {
  const { t, i18n } = useTranslation();
  const [rows, setRows] = useState<TimelineEntry[] | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load(pageToLoad: number, append: boolean) {
    (append ? setLoadingMore : setLoading)(true);
    setError(null);
    getRecordTimeline(entityType, entityId, pageToLoad, PAGE_SIZE)
      .then((res) => {
        setRows((prev) => (append && prev ? [...prev, ...res.items] : res.items));
        setTotal(res.total);
        setPage(res.page);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => (append ? setLoadingMore : setLoading)(false));
  }

  useEffect(() => {
    load(1, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityType, entityId]);

  if (loading) return <ListSkeleton rows={3} title={false} />;
  if (error) return <ErrorState message={error} onRetry={() => load(1, false)} />;
  if (!rows || rows.length === 0) {
    return <EmptyState title={t("timeline.empty")} hint={t("timeline.emptyHint")} />;
  }

  return (
    <div className="record-timeline">
      <ol className="record-timeline__list">
        {rows.map((entry, i) => (
          <li key={i} className="record-timeline__row">
            <div className="record-timeline__head">
              <span className="record-timeline__verb">
                {t(`audit.events.${entry.event}`, humanize(entry.event), entry.params)}
              </span>
              {entry.actor && <span className="record-timeline__actor">{entry.actor}</span>}
              {entry.source && (
                <Tooltip label={t(`timeline.source.${entry.source}`)}>
                  <span className="record-timeline__source">
                    <NavIcon name={entry.source === "ai" ? "sparkle" : "download"} />
                  </span>
                </Tooltip>
              )}
              <span className="record-timeline__time latin">{relativeTime(entry.at, i18n.language)}</span>
            </div>
            {entry.changes.length > 0 && (
              <ul className="record-timeline__changes">
                {entry.changes.map((c) => (
                  <li key={c.field} className="record-timeline__change">
                    <span className="record-timeline__field">
                      {t(`timeline.field.${c.field}`, humanize(c.field))}
                    </span>
                    <span className="record-timeline__chip">
                      <Bdi>{formatValue(c.field, c.old, t)}</Bdi> → <Bdi>{formatValue(c.field, c.new, t)}</Bdi>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
      {rows.length < total && (
        <button
          type="button"
          className="btn btn--text record-timeline__toggle"
          disabled={loadingMore}
          onClick={() => load(page + 1, true)}
        >
          {loadingMore ? t("common.loading") : t("timeline.loadMore")}
        </button>
      )}
    </div>
  );
}
