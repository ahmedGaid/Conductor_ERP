import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { listInstances } from "../api/workflows";
import type { InstanceStatus, InstanceSummary } from "../api/types";
import { useAsync } from "../hooks/useAsync";
import { ErrorState } from "../components/ErrorState";
import { useListKeyboardNav } from "../hooks/useListKeyboardNav";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../lib/filters";
import { useListPageActions } from "../hooks/useListPageActions";
import type { CsvColumn } from "../lib/csvExport";
import { EmptyState } from "../components/EmptyState";
import { FilterBar } from "../components/FilterBar";
import { StatusPill } from "../components/StatusPill";
import { StatusTabs, ALL_TAB } from "../components/StatusTabs";
import { ListSkeleton } from "../components/ListSkeleton";
import { relativeTime } from "../lib/relativeTime";
import { WorkflowNav } from "./WorkflowNav";
import "./WorkflowListPage.css";

const INSTANCE_STATUSES: InstanceStatus[] = ["pending", "running", "waiting", "failed", "completed"];

export function InstanceListPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const workflowId = searchParams.get("workflow") ?? undefined;
  const lang = i18n.resolvedLanguage || i18n.language || "ar";

  const { data, loading, error, reload } = useAsync(
    () => listInstances(workflowId ? { workflow: workflowId } : {}),
    [workflowId],
    `workflow:instances:${workflowId ?? "all"}`,
  );
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<InstanceSummary>[]>(
    () => [
      { key: "workflow_name", label: t("workflow.name"), type: "text", accessor: (i) => i.workflow_name },
      {
        key: "status",
        label: t("common.status"),
        type: "select",
        options: INSTANCE_STATUSES.map((s) => ({ value: s, label: t(`status.${s}`) })),
        accessor: (i) => i.status,
      },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((i) => matchesAllFilters(i, fields, filters)) : data),
    [data, fields, filters],
  );

  const statusTabs = useMemo(
    () => INSTANCE_STATUSES.map((s) => ({ value: s, label: t(`status.${s}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((i) => i.status === tab)) : filtered),
    [filtered, tab],
  );

  const { active } = useListKeyboardNav<InstanceSummary>({
    items: visible ?? [],
    onOpen: (inst) => navigate(`/instances/${inst.id}`),
    persistKey: "workflow-instances",
    getItemId: (inst) => inst.id,
  });

  const csvColumns = useMemo<CsvColumn<InstanceSummary>[]>(
    () => [
      { header: t("workflow.name"), accessor: (i) => i.workflow_name },
      { header: t("common.status"), accessor: (i) => t(`status.${i.status}`) },
      { header: t("instance.list.node"), accessor: (i) => i.current_node ?? "" },
      { header: t("instance.list.created"), accessor: (i) => i.created_at },
    ],
    [t],
  );
  useListPageActions({ rows: visible, columns: csvColumns, filename: "workflow-instances" });

  return (
    <section className="wf-list">
      <WorkflowNav />

      <div className="wf-list__head">
        {data && data.length > 0 && <FilterBar fields={fields} filters={filters} onChange={setFilters} />}
      </div>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("instance.list.empty")} hint={t("instance.list.emptyHint")} />
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={statusTabs}
          accessor={(i) => i.status}
          value={tab}
          onChange={setTab}
          ariaLabel={t("common.status")}
        />
      )}
      {data && data.length > 0 && visible && visible.length === 0 && (
        <EmptyState
          title={t("filter.noMatch")}
          hint={t("filter.noMatchHint")}
          action={{ label: t("filter.clearAll"), onClick: () => setFilters([]) }}
        />
      )}

      {visible && visible.length > 0 && (
        <div className="card wf-list__table-wrap">
          <table className="wf-list__table">
            <thead>
              <tr>
                <th>{t("workflow.name")}</th>
                <th>{t("common.status")}</th>
                <th>{t("instance.list.node")}</th>
                <th>{t("instance.list.created")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((inst, i) => (
                <tr key={inst.id} data-kbd-active={i === active ? "true" : undefined} aria-selected={i === active}>
                  <td>
                    <Link to={`/instances/${inst.id}`}>{inst.workflow_name}</Link>
                  </td>
                  <td>
                    <StatusPill status={inst.status} />
                  </td>
                  <td className="latin">{inst.current_node ?? "—"}</td>
                  <td className="latin">{relativeTime(inst.created_at, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
