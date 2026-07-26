import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { NavIcon } from "../../app/icons";
import { useToast } from "../../app/ToastContext";
import { ApiError, downloadExport } from "../../api/client";
import { useAsync } from "../../hooks/useAsync";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { ErrorState } from "../../components/ErrorState";
import {
  approveOpeningCorrection,
  entityLabelKey,
  getImportReport,
  rollbackImport,
  type ImportBatch,
} from "../../api/smartImports";
import { OpeningCorrectionBanner } from "./OpeningCorrectionBanner";

// Only entities with an actual list page today get a deep link (spec: "verifiable by click") —
// an entity without one just reads as plain text rather than a link to nowhere.
const ENTITY_ROUTES: Record<string, string> = {
  customers: "/sales/customers",
  suppliers: "/purchasing/suppliers",
  items: "/inventory/items",
  journal_entries: "/accounting/journals",
  sales_orders: "/sales",
  sales_quotations: "/sales/quotations",
  purchase_orders: "/purchasing",
};

function EntityLine({ entity, children }: { entity: string; children: ReactNode }) {
  const route = ENTITY_ROUTES[entity];
  if (!route) return <span dir="auto">{children}</span>;
  return (
    <Link to={route} dir="auto">
      {children}
    </Link>
  );
}

interface Group {
  entity: string;
  count: number;
}

function groupMasters(masters: { entity: string; value: string; pk: string }[]): Group[] {
  const byEntity = new Map<string, number>();
  for (const m of masters) byEntity.set(m.entity, (byEntity.get(m.entity) ?? 0) + 1);
  return [...byEntity.entries()].map(([entity, count]) => ({ entity, count }));
}

export function ImportReport({
  batch,
  onRolledBack,
  onNeedsReview,
}: {
  batch: ImportBatch;
  onRolledBack?: () => void;
  onNeedsReview?: () => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const { data: report, loading, error, reload } = useAsync(
    () => getImportReport(batch.id),
    [batch.id],
    `imports:report:${batch.id}`,
  );
  const [rollbackOpen, setRollbackOpen] = useState(false);
  const [rollingBack, setRollingBack] = useState(false);
  const [openingApproving, setOpeningApproving] = useState(false);

  const entityLabel = t(entityLabelKey(batch.entity), batch.entity);
  const openingCorrection = batch.stats?.opening_correction;

  async function onApproveOpeningCorrection() {
    setOpeningApproving(true);
    try {
      await approveOpeningCorrection(batch.id);
      // The batch just left `done` (back to `previewing`) — hand control back to the wizard so it
      // re-routes to Review instead of RunStep re-rendering this same Report with stale status.
      onNeedsReview?.();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
    } finally {
      setOpeningApproving(false);
    }
  }

  async function onRollback() {
    setRollingBack(true);
    try {
      await rollbackImport(batch.id);
      toast.show(t("imports.report.rollback.done"), "success");
      onRolledBack?.();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
    } finally {
      setRollingBack(false);
    }
  }

  if (loading) return <div className="imports-loading" aria-busy="true" />;
  if (error || !report) return <ErrorState message={error} onRetry={reload} />;

  const masterGroups = groupMasters(report.created_masters);
  const rollback = batch.stats?.rollback;

  return (
    <div className="imports-report card">
      <header className="imports-report__head">
        <NavIcon name={batch.status === "rolled_back" ? "rotate" : "check"} />
        <h2 dir="auto">
          {batch.status === "rolled_back" ? t("imports.report.rolledBackTitle") : t("imports.report.doneTitle")}
        </h2>
      </header>

      {openingCorrection && (
        <OpeningCorrectionBanner
          correction={openingCorrection}
          approving={openingApproving}
          onApprove={() => void onApproveOpeningCorrection()}
        />
      )}

      <ul className="imports-report__counts">
        <li>
          <EntityLine entity={batch.entity}>
            {t("imports.report.created", { count: report.created, entity: entityLabel })}
          </EntityLine>
        </li>
        {report.updated > 0 && (
          <li>
            <EntityLine entity={batch.entity}>{t("imports.report.updated", { count: report.updated })}</EntityLine>
          </li>
        )}
        {report.skipped > 0 && <li className="muted">{t("imports.report.skipped", { count: report.skipped })}</li>}
        {report.errors > 0 && (
          <li className="imports-report__errors">{t("imports.report.errors", { count: report.errors })}</li>
        )}
      </ul>

      {masterGroups.length > 0 && (
        <div className="imports-report__masters">
          <p className="imports-report__masters-title muted">{t("imports.report.mastersTitle")}</p>
          <ul>
            {masterGroups.map((g) => (
              <li key={g.entity}>
                <EntityLine entity={g.entity}>
                  {t("imports.report.newMasters", { count: g.count, entity: t(entityLabelKey(g.entity), g.entity) })}
                </EntityLine>
              </li>
            ))}
          </ul>
        </div>
      )}

      {report.duration_seconds !== null && (
        <p className="imports-report__duration muted">
          {t("imports.report.duration", { seconds: Math.round(report.duration_seconds) })}
        </p>
      )}

      {rollback && (
        <div className="imports-report__rollback-summary">
          <p dir="auto">
            {t("imports.report.rollback.summary", {
              reverted: rollback.reverted,
              skipped: rollback.cannot.length,
            })}
          </p>
          {rollback.cannot.length > 0 && (
            <ul className="imports-report__cannot">
              {rollback.cannot.map((c, i) => (
                <li key={i} className="muted" dir="auto">
                  {t(`imports.report.rollback.cannotReason.${c.code ?? "delete_failed"}`, {
                    entity: c.entity ? t(entityLabelKey(c.entity)) : "",
                    defaultValue: t("imports.report.rollback.cannotReason.delete_failed"),
                  })}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <footer className="imports-report__actions">
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => void downloadExport(`/imports/${batch.id}/report?format=csv`, `import-${batch.id}-report.csv`)}
        >
          {t("imports.report.downloadCsv")}
        </button>
        {batch.status === "done" && (report.created > 0 || report.updated > 0) && (
          <button type="button" className="btn btn--ghost" onClick={() => setRollbackOpen(true)}>
            {t("imports.report.rollback.trigger")}
          </button>
        )}
      </footer>

      <ConfirmDialog
        open={rollbackOpen}
        title={t("imports.report.rollback.confirmTitle")}
        body={t("imports.report.rollback.confirmBody")}
        confirmLabel={t("imports.report.rollback.confirm")}
        danger
        onConfirm={() => void onRollback()}
        onClose={() => setRollbackOpen(false)}
      />
      {rollingBack && <div className="imports-loading" aria-busy="true" />}
    </div>
  );
}
