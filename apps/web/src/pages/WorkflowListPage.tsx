import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { listWorkflows } from "../api/workflows";
import { useAsync } from "../hooks/useAsync";
import { ErrorState } from "../components/ErrorState";
import { useListKeyboardNav } from "../hooks/useListKeyboardNav";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../lib/filters";
import { Bdi } from "../components/Bdi";
import { EmptyState } from "../components/EmptyState";
import { FilterBar } from "../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../components/StatusTabs";
import "./WorkflowListPage.css";

type Workflow = Awaited<ReturnType<typeof listWorkflows>>[number];

export function WorkflowListPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listWorkflows, [], "workflows");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<Workflow>[]>(() => {
    const statuses = Array.from(new Set((data ?? []).map((w) => w.status)));
    return [
      { key: "name", label: t("workflow.name"), type: "text", accessor: (w) => w.name },
      {
        key: "status",
        label: t("workflow.status"),
        type: "select",
        options: statuses.map((s) => ({ value: s, label: t(`workflow.statusValue.${s}`, s) })),
        accessor: (w) => w.status,
      },
    ];
  }, [t, data]);
  const filtered = useMemo(
    () => (data ? data.filter((w) => matchesAllFilters(w, fields, filters)) : data),
    [data, fields, filters],
  );

  const statusTabs = useMemo(
    () =>
      Array.from(new Set((data ?? []).map((w) => w.status))).map((s) => ({
        value: s,
        label: t(`workflow.statusValue.${s}`, s),
      })),
    [t, data],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((w) => w.status === tab)) : filtered),
    [filtered, tab],
  );

  // j/k move a row highlight, Enter/o opens it on the detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<Workflow>({
    items: visible ?? [],
    onOpen: (wf) => navigate(`/workflows/${wf.id}`),
  });

  return (
    <section className="wf-list">
      <header className="module-head">
        <h1 className="module-head__title">{t("nav.workflows")}</h1>
        <p className="module-head__desc">{t("moduleIntro.workflows")}</p>
      </header>
      <div className="wf-list__head">
        {data && data.length > 0 && <FilterBar fields={fields} filters={filters} onChange={setFilters} />}
        <Link className="btn btn--primary" to="/workflows/new">
          {t("workflow.create")}
        </Link>
      </div>

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState
          title={t("workflow.empty")}
          hint={t("common.emptyHint")}
          action={{ label: t("workflow.create"), to: "/workflows/new" }}
        />
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={statusTabs}
          accessor={(w) => w.status}
          value={tab}
          onChange={setTab}
          ariaLabel={t("workflow.status")}
        />
      )}
      {data && data.length > 0 && visible && visible.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {visible && visible.length > 0 && (
        <div className="card wf-list__table-wrap">
          <table className="wf-list__table">
            <thead>
              <tr>
                <th>{t("workflow.name")}</th>
                <th>{t("workflow.version")}</th>
                <th>{t("workflow.status")}</th>
                <th>{t("workflow.nodes")}</th>
                <th>{t("workflow.instances")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((wf, i) => (
                <tr key={wf.id} data-kbd-active={i === active ? "true" : undefined} aria-selected={i === active}>
                  <td>
                    <Link to={`/workflows/${wf.id}`}>{wf.name}</Link>
                  </td>
                  <td>
                    <Bdi>v{wf.version}</Bdi>
                  </td>
                  <td>{t(`workflow.statusValue.${wf.status}`, wf.status)}</td>
                  <td>
                    <Bdi>{wf.node_count}</Bdi>
                  </td>
                  <td>
                    <Bdi>{wf.instance_count}</Bdi>
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
