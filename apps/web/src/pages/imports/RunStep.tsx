import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useToast } from "../../app/ToastContext";
import { ApiError } from "../../api/client";
import { useAsync } from "../../hooks/useAsync";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { ErrorState } from "../../components/ErrorState";
import {
  cancelImport,
  getImportBatch,
  pauseImport,
  resumeImport,
  type ImportBatch,
} from "../../api/smartImports";
import { ImportReport } from "./ImportReport";

const POLL_MS = 1500;
const RUNNING_STATUSES = new Set(["ready", "running", "paused"]);
const DONE_STATUSES = new Set(["done", "rolled_back"]);

function formatEta(seconds: number | null | undefined): string | null {
  if (seconds === null || seconds === undefined) return null;
  if (seconds < 60) return `${Math.ceil(seconds)}s`;
  const minutes = Math.round(seconds / 60);
  return `${minutes}m`;
}

export function RunStep({ batchId }: { batchId: string }) {
  const { t } = useTranslation();
  const toast = useToast();
  const { data: batch, error, reload, mutate } = useAsync<ImportBatch>(
    () => getImportBatch(batchId),
    [batchId],
    `imports:batch:${batchId}`,
  );
  const [cancelOpen, setCancelOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const status = batch?.status;
  const isLive = status ? RUNNING_STATUSES.has(status) : false;

  useEffect(() => {
    if (!isLive) return;
    const id = window.setInterval(reload, POLL_MS);
    return () => window.clearInterval(id);
  }, [isLive, reload]);

  if (error && !batch) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  if (!batch) {
    return <div className="imports-loading" aria-busy="true" />;
  }

  if (DONE_STATUSES.has(batch.status)) {
    // A real refetch (not an optimistic patch) — the reversal summary needs the server's
    // authoritative `stats.rollback` (reverted/skipped/cannot counts), which only exists after
    // `rollback_batch` writes it.
    return <ImportReport batch={batch} onRolledBack={reload} />;
  }

  const stats = batch.stats ?? {};
  const rowsDone = stats.rows_done ?? batch.processed_count;
  const total = batch.row_count || 1;
  const pct = Math.min(100, Math.round((rowsDone / total) * 100));
  const eta = formatEta(stats.eta_seconds);
  const stage = stats.stage === "importing" ? t("imports.run.stage.importing") : t("imports.run.stage.queued");

  async function onPause() {
    setBusy(true);
    try {
      await pauseImport(batchId);
      toast.show(t("imports.run.pauseRequested"), "info");
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
    } finally {
      setBusy(false);
    }
  }

  async function onResume() {
    setBusy(true);
    try {
      const updated = await resumeImport(batchId);
      mutate(updated);
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
    } finally {
      setBusy(false);
    }
  }

  async function onCancel() {
    setBusy(true);
    try {
      await cancelImport(batchId);
      toast.show(t("imports.run.cancelRequested"), "info");
      reload();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="imports-run card">
      <p className="imports-run__stage" dir="auto">{stage}</p>

      <div className="imports-run__bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <span className="imports-run__bar-fill" style={{ inlineSize: `${pct}%` }} />
      </div>

      <p className="imports-run__count muted">
        {t("imports.run.rowsOf", { done: rowsDone, total: batch.row_count })}
        {stats.rows_per_sec ? ` · ${t("imports.run.perSecond", { rate: stats.rows_per_sec })}` : ""}
        {eta ? ` · ${t("imports.run.etaLeft", { eta })}` : ""}
      </p>

      {batch.status === "paused" && (
        <p className="imports-run__notice" role="status">
          {t("imports.run.pausedNotice", { count: rowsDone })}
        </p>
      )}

      <div className="imports-run__actions">
        {batch.status === "paused" ? (
          <button type="button" className="btn btn--primary" disabled={busy} onClick={() => void onResume()}>
            {t("imports.run.resume")}
          </button>
        ) : (
          <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => void onPause()}>
            {t("imports.run.pause")}
          </button>
        )}
        <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => setCancelOpen(true)}>
          {t("imports.run.cancel")}
        </button>
      </div>

      <ConfirmDialog
        open={cancelOpen}
        title={t("imports.run.cancelConfirm.title")}
        body={t("imports.run.cancelConfirm.body", { count: rowsDone })}
        confirmLabel={t("imports.run.cancelConfirm.confirm")}
        danger
        onConfirm={() => void onCancel()}
        onClose={() => setCancelOpen(false)}
      />
    </div>
  );
}
