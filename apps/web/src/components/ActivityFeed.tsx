import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  completeActivity,
  listActivities,
  logActivity,
  type Activity,
  type ActivityType,
  type RelatedType,
} from "../api/crm";
import { useAsync } from "../hooks/useAsync";
import { useToast } from "../app/ToastContext";
import { optimisticCreate, runOptimistic } from "../lib/optimistic";
import { Badge, type BadgeTone } from "./Badge";
import { Bdi } from "./Bdi";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { ListSkeleton } from "./ListSkeleton";
import "./activityFeed.css";

const TYPES: ActivityType[] = ["call", "email", "meeting", "task", "note"];

const MS_PER_DAY = 1000 * 60 * 60 * 24;

function daysUntil(dateStr: string): number {
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / MS_PER_DAY);
}

// Same three-step reading as the batch-expiry badge: past due is the only alarming state, the
// next few days are worth noticing, everything further out stays quiet.
function dueTone(days: number): BadgeTone {
  if (days < 0) return "failed";
  if (days <= 3) return "waiting";
  return "neutral";
}

/**
 * The human side of a CRM record's history: the calls, emails, meetings, tasks and notes people
 * log against one lead, opportunity or ticket. Deliberately NOT `RecordTimeline` — that one reads
 * the system's own audit trail (who changed which field), while this one is what a salesperson
 * typed. Both can sit on the same record without saying the same thing twice.
 *
 * Open items come first (the backend orders `done, due_date, -created_at`), so the feed answers
 * "what do I still owe this deal?" before "what happened". Logging and completing are optimistic:
 * the row appears or ticks over instantly, and rolls back with a toast if the server refuses.
 */
export function ActivityFeed({
  relatedType,
  relatedRef,
}: {
  relatedType: RelatedType;
  relatedRef: string;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync<Activity[]>(
    () => listActivities(relatedType, relatedRef),
    [relatedType, relatedRef],
    `crm:activities:${relatedType}:${relatedRef}`,
  );

  const [type, setType] = useState<ActivityType>("call");
  const [subject, setSubject] = useState("");

  function onLog(e: FormEvent) {
    e.preventDefault();
    const s = subject.trim();
    if (!s) {
      toast.show(t("crm.activity.needSubject"), "error");
      return;
    }
    void optimisticCreate<Activity>({
      current: data ?? [],
      mutate,
      placeholder: (id) =>
        ({
          id,
          type,
          subject: s,
          related_type: relatedType,
          related_ref: relatedRef,
          owner: "",
          due_date: null,
          done: false,
          notes: "",
        }) as Activity,
      request: () => logActivity({ type, subject: s, related_type: relatedType, related_ref: relatedRef }),
      toast,
      success: t("crm.toast.activityLogged"),
    });
    setSubject("");
  }

  function onComplete(activity: Activity) {
    if (!data) return;
    void runOptimistic<Activity[], Activity>({
      current: data,
      mutate,
      optimistic: (rows) => rows.map((a) => (a.id === activity.id ? { ...a, done: true } : a)),
      request: () => completeActivity(activity.id),
      settle: (predicted, updated) => predicted.map((a) => (a.id === updated.id ? updated : a)),
      toast,
      success: t("crm.toast.activityCompleted"),
    });
  }

  return (
    <div className="activity-feed">
      <h3 className="activity-feed__title">{t("crm.activity.title")}</h3>

      <form className="activity-feed__form" onSubmit={onLog}>
        <label className="activity-feed__field">
          <span>{t("crm.activity.subject")}</span>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder={t("crm.activity.subjectPlaceholder")}
          />
        </label>
        {/* Five fixed kinds — a native select is the right control at this size. */}
        <label className="activity-feed__field activity-feed__field--type">
          <span>{t("crm.activity.typeLabel")}</span>
          <select value={type} onChange={(e) => setType(e.target.value as ActivityType)}>
            {TYPES.map((tp) => (
              <option key={tp} value={tp}>
                {t(`crm.activity.type.${tp}`)}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="btn btn--primary">
          {t("crm.activity.log")}
        </button>
      </form>

      {loading && <ListSkeleton rows={3} title={false} />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <EmptyState title={t("crm.activity.empty")} hint={t("crm.activity.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <ol className="activity-feed__list">
          {data.map((a) => {
            const days = a.due_date ? daysUntil(a.due_date) : null;
            return (
              <li key={a.id} className="activity-feed__row" data-done={a.done ? "true" : undefined}>
                <span className="activity-feed__kind">{t(`crm.activity.type.${a.type}`)}</span>
                <span className="activity-feed__subject">
                  <Bdi>{a.subject}</Bdi>
                </span>
                {a.owner && <span className="activity-feed__owner">{a.owner}</span>}
                {a.due_date && days !== null && !a.done && (
                  <Badge tone={dueTone(days)}>
                    {days < 0
                      ? t(Math.abs(days) === 1 ? "crm.activity.overdueOne" : "crm.activity.overdue", {
                          count: Math.abs(days),
                        })
                      : days === 0
                        ? t("crm.activity.dueToday")
                        : t(days === 1 ? "crm.activity.dueInOne" : "crm.activity.dueIn", { count: days })}
                  </Badge>
                )}
                {a.done ? (
                  <Badge tone="completed">{t("crm.activity.done")}</Badge>
                ) : (
                  <button type="button" className="btn btn--sm" onClick={() => onComplete(a)}>
                    {t("crm.activity.complete")}
                  </button>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
