import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../../app/icons";
import { getSystemStatus, type HealthStatus, type SystemStatus } from "../../api/system";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { Bdi } from "../../components/Bdi";
import { relativeTime } from "../../lib/relativeTime";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import "./settings.css";
import "./system.css";

// Auto-refresh cadence — settled, not a live-poll dashboard (the panel is diagnostic, not
// operational). A manual refresh action covers "I just fixed it, show me now".
const REFRESH_MS = 30_000;

function bytes(n: number | null): string {
  if (n === null) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function duration(totalSeconds: number, t: (key: string, opts?: Record<string, unknown>) => string): string {
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (days > 0) return t("settings.system.uptimeDays", { days, hours });
  if (hours > 0) return t("settings.system.uptimeHours", { hours, minutes });
  return t("settings.system.uptimeMinutes", { minutes });
}

function StatusWord({ status }: { status: HealthStatus }) {
  const { t } = useTranslation();
  return (
    <span className={`sysrow__status sysrow__status--${status}`}>
      <NavIcon name={status === "healthy" ? "checkCircle" : "warning"} />
      {t(`settings.system.status.${status}`)}
    </span>
  );
}

function Row({
  label,
  status,
  detail,
}: {
  label: string;
  status: HealthStatus;
  detail?: string;
}) {
  return (
    <div className="sysrow">
      <span className="sysrow__label">{label}</span>
      <StatusWord status={status} />
      {detail && <span className="sysrow__detail"><Bdi>{detail}</Bdi></span>}
    </div>
  );
}

function ActionableLine({ status, hint }: { status: HealthStatus; hint: string }) {
  if (status === "healthy") return null;
  return <p className="sysrow__hint">{hint}</p>;
}

function SystemContent({ data, refreshing, onRefresh }: { data: SystemStatus; refreshing: boolean; onRefresh: () => void }) {
  const { t, i18n } = useTranslation();

  return (
    <div className="card setcard">
      <p className="setcard__lead">{t("settings.system.lead")}</p>
      {data.status !== "healthy" && (
        <div className={`sysbanner sysbanner--${data.status}`} role="status">
          <NavIcon name="warning" />
          <span>{t(`settings.system.banner.${data.status}`)}</span>
        </div>
      )}

      <div className="setrow">
        <span className="setrow__label">
          <span className="setrow__title">{t("settings.system.version")}</span>
        </span>
        <span className="setrow__control"><Bdi>{data.version}</Bdi></span>
      </div>
      <div className="setrow">
        <span className="setrow__label">
          <span className="setrow__title">{t("settings.system.uptime")}</span>
        </span>
        <span className="setrow__control">{duration(data.uptime_seconds, t)}</span>
      </div>

      <div className="setcard__block">
        <Row label={t("settings.system.database")} status={data.database.status} detail={`${data.database.latency_ms} ms`} />
        <ActionableLine status={data.database.status} hint={t("settings.system.hint.database")} />

        <Row label={t("settings.system.redis")} status={data.redis.status} detail={`${data.redis.latency_ms} ms`} />
        <ActionableLine status={data.redis.status} hint={t("settings.system.hint.redis")} />

        <Row
          label={t("settings.system.storage")}
          status={data.storage.status}
          detail={
            data.storage.free_bytes !== null && data.storage.total_bytes !== null
              ? t("settings.system.storageFree", { free: bytes(data.storage.free_bytes), total: bytes(data.storage.total_bytes) })
              : undefined
          }
        />
        <ActionableLine status={data.storage.status} hint={t("settings.system.hint.storage")} />

        <Row
          label={t("settings.system.workers")}
          status={data.workers.status}
          detail={
            data.workers.queue_depth !== null
              ? t("settings.system.workersDetail", { count: data.workers.count, depth: data.workers.queue_depth })
              : t("settings.system.workersCount", { count: data.workers.count })
          }
        />
        <ActionableLine status={data.workers.status} hint={t("settings.system.hint.workers")} />
      </div>

      <div className="setcard__block">
        <div className="setrow">
          <span className="setrow__label">
            <span className="setrow__title">{t("settings.system.backup")}</span>
            <span className="setrow__desc">{t("settings.system.backupDesc")}</span>
          </span>
          <span className="setrow__control">
            {data.backup.configured
              ? data.backup.last_backup_at
                ? relativeTime(data.backup.last_backup_at, i18n.language)
                : t("settings.system.backupNoneYet")
              : t("settings.system.backupNotConfigured")}
          </span>
        </div>
      </div>

      <div className="setcard__block">
        <p className="setrow__title">{t("settings.system.envTitle")}</p>
        <p className="setrow__desc">{t("settings.system.envDesc")}</p>
        <table className="admin-table sys-env-table">
          <thead>
            <tr>
              <th>{t("settings.system.envName")}</th>
              <th>{t("settings.system.envState")}</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data.env).map(([name, state]) => (
              <tr key={name}>
                <td className="latin">{name}</td>
                <td>
                  <span className={`sysrow__status sysrow__status--${state === "set" ? "healthy" : "unset"}`}>
                    {t(`settings.system.envValue.${state}`)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="setcard__block">
        <button type="button" className="btn btn--sm" onClick={onRefresh} disabled={refreshing}>
          {t("settings.system.refresh")}
        </button>
      </div>
    </div>
  );
}

export function SystemPage() {
  const { data, loading, error, errorStatus, reload, validating } = useAsync(getSystemStatus, [], "settings:system-status");

  useEffect(() => {
    const id = window.setInterval(reload, REFRESH_MS);
    return () => window.clearInterval(id);
  }, [reload]);

  return (
    <section className="page-enter">
      <SettingsNav />
      {loading && <SettingsSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} status={errorStatus} />}
      {data && <SystemContent data={data} refreshing={validating} onRefresh={reload} />}
    </section>
  );
}
