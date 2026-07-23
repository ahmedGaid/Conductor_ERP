import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { NavIcon } from "../../app/icons";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { useAsync } from "../../hooks/useAsync";
import { entityLabelKey, listImportBatches, type ImportBatch } from "../../api/smartImports";
import "./imports.css";

const PAGE_SIZE = 25;
const ROLLBACK_ELIGIBLE = new Set(["done"]);

function StatusPill({ status }: { status: string }) {
  const { t } = useTranslation();
  const icon =
    status === "done" ? "check" :
    status === "rolled_back" ? "rotate" :
    status === "running" ? "clock" :
    status === "paused" ? "warning" : "info";
  return (
    <span className={`imports-history__status imports-history__status--${status}`}>
      <NavIcon name={icon} />
      {t(`imports.history.status.${status}`, status)}
    </span>
  );
}

export function ImportHistory() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(
    () => listImportBatches({ page, page_size: PAGE_SIZE }),
    [page],
    `imports:history:${page}`,
  );

  if (loading) return <div className="imports-loading" aria-busy="true" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const batches = data?.batches ?? [];

  return (
    <section className="imports-page imports-page--wide">
      <header className="imports-page__head imports-history__head">
        <div>
          <h1 className="imports-page__title">{t("imports.history.title")}</h1>
          <p className="imports-page__lede">{t("imports.history.lede")}</p>
        </div>
        <Link to="/imports/new" className="btn btn--primary">
          {t("imports.history.newImport")}
        </Link>
      </header>

      {batches.length === 0 ? (
        <EmptyState
          icon={<NavIcon name="import" />}
          title={t("imports.history.empty.title")}
          hint={t("imports.history.empty.hint")}
          action={{ label: t("imports.history.newImport"), to: "/imports/new" }}
        />
      ) : (
        <div className="imports-history__table-wrap">
          <table className="imports-history__table">
            <thead>
              <tr>
                <th scope="col">{t("imports.history.fileHeader")}</th>
                <th scope="col">{t("imports.history.entityHeader")}</th>
                <th scope="col">{t("imports.history.byHeader")}</th>
                <th scope="col">{t("imports.history.whenHeader")}</th>
                <th scope="col">{t("imports.history.rowsHeader")}</th>
                <th scope="col">{t("imports.history.statusHeader")}</th>
                <th scope="col">{t("imports.history.rollbackHeader")}</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((b: ImportBatch) => (
                <tr
                  key={b.id}
                  className="imports-history__row"
                  tabIndex={0}
                  onClick={() => navigate(`/imports/${b.id}`)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") navigate(`/imports/${b.id}`);
                  }}
                >
                  <td dir="auto"><Bdi>{b.file_name ?? "—"}</Bdi></td>
                  <td dir="auto">{t(entityLabelKey(b.entity), b.entity)}</td>
                  <td dir="auto">{b.created_by_name ?? "—"}</td>
                  <td className="muted">{new Date(b.created_at).toLocaleString()}</td>
                  <td className="muted">
                    {t("imports.history.rowsCount", { count: b.row_count })}
                    {b.error_count > 0 ? ` · ${t("imports.history.errorsCount", { count: b.error_count })}` : ""}
                  </td>
                  <td><StatusPill status={b.status} /></td>
                  <td className="muted">
                    {b.status === "rolled_back"
                      ? t("imports.history.rolledBack")
                      : ROLLBACK_ELIGIBLE.has(b.status)
                        ? t("imports.history.rollbackAvailable")
                        : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && data.total > PAGE_SIZE && (
        <div className="imports-review__pager">
          <button type="button" className="btn btn--ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            {t("imports.review.prevPage")}
          </button>
          <span className="muted">
            {t("imports.review.pageOf", {
              from: (page - 1) * PAGE_SIZE + 1,
              to: Math.min(page * PAGE_SIZE, data.total),
              total: data.total,
            })}
          </span>
          <button
            type="button"
            className="btn btn--ghost"
            disabled={page * PAGE_SIZE >= data.total}
            onClick={() => setPage((p) => p + 1)}
          >
            {t("imports.review.nextPage")}
          </button>
        </div>
      )}
    </section>
  );
}
