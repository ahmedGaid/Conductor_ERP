import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  listNotifications,
  resendNotification,
  type Notification,
  type NotificationStatus,
} from "../../api/notifications";
import { useAsync } from "../../hooks/useAsync";
import { Bdi } from "../../components/Bdi";
import { Tooltip } from "../../components/Tooltip";
import { SegmentedControl } from "../../components/SegmentedControl";
import { ExportButtons } from "../../components/ExportButtons";
import { EmptyState } from "../../components/EmptyState";
import { NotificationsNav } from "./NotificationsNav";
import "./notifications.css";

const STATUSES: (NotificationStatus | "")[] = ["", "sent", "failed", "pending"];

export function NotificationsPage() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<NotificationStatus | "">("");
  const { data, loading, error, reload } = useAsync(
    () => listNotifications(status ? { status } : undefined),
    [status],
    `notifications:${status || "all"}`,
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function resend(id: string) {
    setBusy(id);
    setActionError(null);
    try {
      await resendNotification(id);
      reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="ntf-page">
      <NotificationsNav />

      <div className="ntf-filters">
        <SegmentedControl
          ariaLabel={t("notifications.filterStatus")}
          value={status}
          onChange={setStatus}
          options={STATUSES.map((s) => ({
            value: s,
            label: s ? t(`notifications.status.${s}`) : t("notifications.allStatuses"),
          }))}
        />
      </div>

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}
      {actionError && <p className="error-text">{actionError}</p>}
      {data && data.length === 0 && <EmptyState title={t("notifications.empty")} hint={t("notifications.emptyHint")} />}

      {data && data.length > 0 && <ExportButtons path="/notifications" />}

      {data && data.length > 0 && (
        <div className="card ntf-table-wrap">
          <table className="ntf-table">
            <thead>
              <tr>
                <th>{t("notifications.channel")}</th>
                <th>{t("notifications.recipient")}</th>
                <th>{t("notifications.subject")}</th>
                <th>{t("notifications.reference")}</th>
                <th>{t("notifications.statusHeader")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((n: Notification) => (
                <tr key={n.id}>
                  <td>
                    <span className={`ntf-chan ntf-chan--${n.channel}`}>
                      {t(`notifications.channels.${n.channel}`)}
                    </span>
                  </td>
                  <td className="latin"><Bdi>{n.recipient}</Bdi></td>
                  <td>{n.subject}</td>
                  <td className="latin muted">{n.reference || "—"}</td>
                  <td>
                    <Tooltip label={n.error_text || ""} placement="top">
                      <span className={`ntf-badge ntf-badge--${n.status}`}>
                        {t(`notifications.status.${n.status}`)}
                      </span>
                    </Tooltip>
                  </td>
                  <td>
                    <button className="btn btn--sm" disabled={busy === n.id} onClick={() => resend(n.id)}>
                      {t("notifications.resend")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
