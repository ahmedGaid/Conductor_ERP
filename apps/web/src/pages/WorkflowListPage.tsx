import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { listWorkflows } from "../api/workflows";
import { useAsync } from "../hooks/useAsync";
import { Bdi } from "../components/Bdi";
import { EmptyState } from "../components/EmptyState";
import "./WorkflowListPage.css";

export function WorkflowListPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(listWorkflows, [], "workflows");

  return (
    <section className="wf-list">
      <header className="module-head">
        <h1 className="module-head__title">{t("nav.workflows")}</h1>
        <p className="module-head__desc">{t("moduleIntro.workflows")}</p>
      </header>
      <div className="wf-list__head">
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
      {error && <p className="error-text">{error}</p>}

      {data && data.length === 0 && (
        <EmptyState
          title={t("workflow.empty")}
          hint={t("common.emptyHint")}
          action={{ label: t("workflow.create"), to: "/workflows/new" }}
        />
      )}

      {data && data.length > 0 && (
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
              {data.map((wf) => (
                <tr key={wf.id}>
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
