import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";

import { getRecordHistory } from "../api/audit";
import { useAsync } from "../hooks/useAsync";
import { formatMinor } from "../lib/money";
import { relativeTime } from "../lib/relativeTime";
import { Bdi } from "./Bdi";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { ListSkeleton } from "./ListSkeleton";
import "./recordTimeline.css";

const COLLAPSE_TO = 5;

// snake_case field/action codes fall back to a readable phrase when no i18n key covers them yet
// (the audit trail spans every module, so the dictionary only needs to grow where it reads oddly).
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
 * "old -> new" lines come from the backend comparing consecutive snapshots (`erp/audit/history.py`).
 * Collapsed to the last 5 by default; blame-free tone throughout (states facts, not fault).
 */
export function RecordTimeline({ entityType, entityId }: { entityType: string; entityId: string }) {
  const { t, i18n } = useTranslation();
  const { data, loading, error, reload } = useAsync(
    () => getRecordHistory(entityType, entityId),
    [entityType, entityId],
    `audit:timeline:${entityType}:${entityId}`,
  );
  const [expanded, setExpanded] = useState(false);

  if (loading) return <ListSkeleton rows={3} title={false} />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data || data.length === 0) {
    return <EmptyState title={t("timeline.empty")} hint={t("timeline.emptyHint")} />;
  }

  const rows = expanded ? data : data.slice(0, COLLAPSE_TO);

  return (
    <div className="record-timeline">
      <ol className="record-timeline__list">
        {rows.map((entry, i) => (
          <li key={i} className="record-timeline__row">
            <div className="record-timeline__head">
              <span className="record-timeline__verb">
                {t(`timeline.action.${entry.action}`, humanize(entry.action))}
              </span>
              {entry.actor_name && <span className="record-timeline__actor">{entry.actor_name}</span>}
              <span className="record-timeline__time latin">{relativeTime(entry.at, i18n.language)}</span>
            </div>
            {entry.changes.length > 0 && (
              <ul className="record-timeline__changes">
                {entry.changes.map((c) => (
                  <li key={c.field} className="record-timeline__change">
                    <span className="record-timeline__field">
                      {t(`timeline.field.${c.field}`, humanize(c.field))}
                    </span>
                    {": "}
                    <Bdi>{formatValue(c.field, c.old, t)}</Bdi> → <Bdi>{formatValue(c.field, c.new, t)}</Bdi>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
      {data.length > COLLAPSE_TO && (
        <button
          type="button"
          className="btn btn--text record-timeline__toggle"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? t("timeline.showLess") : t("timeline.showAll")}
        </button>
      )}
    </div>
  );
}
