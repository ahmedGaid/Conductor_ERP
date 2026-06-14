import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { getMetrics } from "../api/workflows";
import type { InstanceStatus } from "../api/types";
import { useAsync } from "../hooks/useAsync";
import { Bdi } from "../components/Bdi";
import "./DashboardPage.css";

const STATUS_ORDER: InstanceStatus[] = [
  "running",
  "waiting",
  "completed",
  "failed",
  "pending",
];

export function DashboardPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(getMetrics, []);

  return (
    <section className="dashboard">
      <div className="dashboard__head">
        <h1>{t("dashboard.heading")}</h1>
        <Link className="btn btn--primary" to="/workflows/new">
          {t("workflow.create")}
        </Link>
      </div>

      {loading && <p className="muted">{t("common.loading")}</p>}
      {error && <p className="error-text">{error}</p>}

      {data && (
        <>
          <div className="dashboard__grid">
            <Metric label={t("dashboard.workflowsTotal")} value={data.workflows_total} />
            <Metric label={t("dashboard.workflowsActive")} value={data.workflows_active} />
            <Metric label={t("dashboard.instancesTotal")} value={data.instances_total} />
            <Metric
              label={t("dashboard.instancesWaiting")}
              value={data.instances_waiting}
              tone="waiting"
            />
            <Metric
              label={t("dashboard.instancesFailed")}
              value={data.instances_failed}
              tone="failed"
            />
          </div>

          <div className="card dashboard__breakdown">
            <h2>{t("dashboard.byStatus")}</h2>
            <ul className="dashboard__statuslist">
              {STATUS_ORDER.map((s) => (
                <li key={s}>
                  <span>{t(`status.${s}`)}</span>
                  <Bdi>{data.instances_by_status[s] ?? 0}</Bdi>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </section>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "waiting" | "failed";
}) {
  return (
    <div className={`metric card${tone ? ` metric--${tone}` : ""}`}>
      <div className="metric__value">
        <Bdi>{value}</Bdi>
      </div>
      <div className="metric__label">{label}</div>
    </div>
  );
}
