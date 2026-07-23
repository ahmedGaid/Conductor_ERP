import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { useToast } from "../../app/ToastContext";
import { ApiError } from "../../api/client";
import {
  applyAutofix,
  buildCreationPlan,
  executeCreationPlan,
  executeImport,
  getAutofixPreview,
  getImportRows,
  patchImportRow,
  type ImportBatch,
  type ImportCreationPlanEntry,
  type ImportFix,
  type ImportRowRow,
} from "../../api/smartImports";
import { CreationPlan } from "./CreationPlan";
import { DuplicateReview } from "./DuplicateReview";
import { PreviewGrid } from "./PreviewGrid";
import { SummaryPanel, type ReviewCounts } from "./SummaryPanel";

type Tab = "all" | "valid" | "error" | "duplicate" | "skipped";
const TABS: Tab[] = ["all", "valid", "error", "duplicate", "skipped"];
const PAGE_SIZE = 25;

function fixKey(f: ImportFix): string {
  return `${f.row_id}:${f.field}:${f.code}`;
}

function AutofixModal({
  fixes,
  selected,
  onToggle,
  applying,
  onApply,
  onClose,
}: {
  fixes: ImportFix[];
  selected: Set<string>;
  onToggle: (key: string) => void;
  applying: boolean;
  onApply: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dlg = ref.current;
    if (!dlg) return;
    if (!dlg.open) dlg.showModal();
  }, []);

  return (
    <dialog
      ref={ref}
      className="imports-autofix"
      aria-label={t("imports.autofix.modalTitle")}
      onClose={onClose}
      onCancel={onClose}
    >
      <div className="imports-autofix__panel">
        <h2 className="imports-autofix__title">{t("imports.autofix.modalTitle")}</h2>
        <p className="imports-autofix__hint muted">{t("imports.autofix.modalHint")}</p>
        <ul className="imports-autofix__list">
          {fixes.map((f) => {
            const key = fixKey(f);
            return (
              <li key={key} className="imports-autofix__fix">
                <label>
                  <input type="checkbox" checked={selected.has(key)} onChange={() => onToggle(key)} />
                  <span className="imports-autofix__desc" dir="auto">
                    {t("imports.autofix.rowField", { row: f.row, field: t(`imports.field.${f.field}`, f.field) })}
                    {" — "}
                    <span className="imports-autofix__from">{String(f.from ?? "—")}</span>
                    {" → "}
                    <span className="imports-autofix__to">{String(f.to ?? "—")}</span>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
        <div className="imports-autofix__actions">
          <button type="button" className="btn" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button
            type="button"
            className="btn btn--primary"
            disabled={applying || selected.size === 0}
            onClick={onApply}
          >
            {applying ? t("common.loading") : t("imports.autofix.apply", { count: selected.size })}
          </button>
        </div>
      </div>
    </dialog>
  );
}

export function ReviewStep({
  batch: initialBatch,
  onImported,
}: {
  batch: ImportBatch;
  onImported: (batchId: string) => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const [batch] = useState(initialBatch);

  const [tab, setTab] = useState<Tab>("all");
  const [page, setPage] = useState(1);
  const [rowsPage, setRowsPage] = useState<{ rows: ImportRowRow[]; total: number } | null>(null);
  const [loadingRows, setLoadingRows] = useState(true);
  const [busyRows, setBusyRows] = useState<Set<number>>(new Set());

  const [counts, setCounts] = useState<ReviewCounts | null>(null);
  const [mergedCount, setMergedCount] = useState(0);

  const [plan, setPlan] = useState<ImportCreationPlanEntry[]>([]);
  const [planApproved, setPlanApproved] = useState<Set<string>>(new Set());
  const [planApplying, setPlanApplying] = useState(false);

  const [autofixFixes, setAutofixFixes] = useState<ImportFix[] | null>(null);
  const [autofixSelected, setAutofixSelected] = useState<Set<string>>(new Set());
  const [autofixApplying, setAutofixApplying] = useState(false);

  const [strategy, setStrategy] = useState<"create_only" | "update_only" | "upsert" | "skip_existing">(
    (batch.strategy as "create_only" | "update_only" | "upsert" | "skip_existing") ?? "create_only",
  );
  const [atomicity, setAtomicity] = useState(true);
  const [continueAfterErrors, setContinueAfterErrors] = useState(false);
  const [importing, setImporting] = useState(false);

  async function refreshCounts() {
    const [valid, error, duplicate, skipped] = await Promise.all([
      getImportRows(batch.id, { status: "valid", page_size: 1 }),
      getImportRows(batch.id, { status: "error", page_size: 1 }),
      getImportRows(batch.id, { status: "duplicate", page_size: 1 }),
      getImportRows(batch.id, { status: "skipped", page_size: 1 }),
    ]);
    setCounts({
      all: batch.row_count,
      valid: valid.total,
      error: error.total,
      duplicate: duplicate.total,
      skipped: skipped.total,
    });
  }

  async function refreshRows() {
    setLoadingRows(true);
    try {
      const res = await getImportRows(batch.id, {
        status: tab === "all" ? undefined : tab,
        page,
        page_size: PAGE_SIZE,
      });
      setRowsPage({ rows: res.rows, total: res.total });
    } finally {
      setLoadingRows(false);
    }
  }

  async function refreshPlan() {
    const res = await buildCreationPlan(batch.id);
    setPlan(res.entries);
    setPlanApproved(new Set());
  }

  useEffect(() => {
    void refreshCounts();
    void refreshPlan();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void refreshRows();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, page]);

  function changeTab(next: Tab) {
    setTab(next);
    setPage(1);
  }

  async function onEditCell(rowNumber: number, field: string, value: unknown) {
    setBusyRows((s) => new Set(s).add(rowNumber));
    try {
      const updated = await patchImportRow(batch.id, rowNumber, { edits: { [field]: value } });
      setRowsPage((p) => (p ? { ...p, rows: p.rows.map((r) => (r.row_number === rowNumber ? updated : r)) } : p));
      void refreshCounts();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
    } finally {
      setBusyRows((s) => {
        const next = new Set(s);
        next.delete(rowNumber);
        return next;
      });
    }
  }

  async function onDecide(rowNumber: number, decision: "merge" | "create" | "ignore", targetPk?: string) {
    setBusyRows((s) => new Set(s).add(rowNumber));
    try {
      await patchImportRow(batch.id, rowNumber, {
        decision: { duplicate: decision, ...(targetPk ? { target_pk: targetPk } : {}) },
      });
      if (decision === "merge") setMergedCount((n) => n + 1);
      await Promise.all([refreshCounts(), refreshRows()]);
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
    } finally {
      setBusyRows((s) => {
        const next = new Set(s);
        next.delete(rowNumber);
        return next;
      });
    }
  }

  function scrollToPlan() {
    document.querySelector(".imports-plan")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function onOpenAutofix() {
    try {
      const res = await getAutofixPreview(batch.id);
      setAutofixFixes(res.fixes);
      setAutofixSelected(new Set(res.fixes.map(fixKey)));
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
    }
  }

  async function onApplyAutofix() {
    if (!autofixFixes) return;
    setAutofixApplying(true);
    try {
      const accepted = autofixFixes.filter((f) => autofixSelected.has(fixKey(f)));
      await applyAutofix(batch.id, accepted);
      setAutofixFixes(null);
      await Promise.all([refreshCounts(), refreshRows()]);
      toast.show(t("imports.autofix.applied", { count: accepted.length }), "success");
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
    } finally {
      setAutofixApplying(false);
    }
  }

  async function onApprovePlan() {
    setPlanApplying(true);
    try {
      const approved = [...planApproved].map((key) => {
        const [entity, ...rest] = key.split(":");
        return { entity, value: rest.join(":") };
      });
      await executeCreationPlan(batch.id, approved);
      await Promise.all([refreshCounts(), refreshRows(), refreshPlan()]);
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
    } finally {
      setPlanApplying(false);
    }
  }

  async function onImport() {
    setImporting(true);
    try {
      await executeImport(batch.id, {
        strategy,
        atomicity,
        continue_after_errors: continueAfterErrors,
      });
      // Whether it ran inline or got queued for the background runner, `RunStep` (session 14)
      // owns everything from here — it polls the batch itself and renders progress or the
      // final report, so this component doesn't need to know which path it took.
      onImported(batch.id);
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
      setImporting(false);
    }
  }

  const planPending = plan.filter(
    (e) => !e.outcome && (e.action === "create" || e.action === "link"),
  ).length;
  const nameField = batch.fields.find((f) => f.name === "name")?.name;

  return (
    <div className="imports-review">
      <div className="imports-review__main">
        <nav className="imports-review__tabs" role="tablist" aria-label={t("imports.review.tabsLabel")}>
          {TABS.map((tb) => (
            <button
              key={tb}
              type="button"
              role="tab"
              aria-selected={tab === tb}
              className={tab === tb ? "imports-review__tab imports-review__tab--on" : "imports-review__tab"}
              onClick={() => changeTab(tb)}
            >
              {t(`imports.review.tab.${tb}`)}
              <span className="imports-review__tab-count">{counts ? counts[tb] : "…"}</span>
            </button>
          ))}
        </nav>

        <CreationPlan
          entries={plan}
          approved={planApproved}
          applying={planApplying}
          onToggle={(key) =>
            setPlanApproved((s) => {
              const next = new Set(s);
              if (next.has(key)) next.delete(key);
              else next.add(key);
              return next;
            })
          }
          onApprove={() => void onApprovePlan()}
        />

        {loadingRows || !rowsPage ? (
          <div className="imports-loading" aria-busy="true" />
        ) : tab === "duplicate" ? (
          <DuplicateReview
            rows={rowsPage.rows}
            nameField={nameField}
            fields={batch.fields}
            busyRows={busyRows}
            onDecide={(row, decision, targetPk) => void onDecide(row, decision, targetPk)}
          />
        ) : (
          <PreviewGrid
            fields={batch.fields}
            rows={rowsPage.rows}
            busyRows={busyRows}
            onEditCell={(row, field, value) => void onEditCell(row, field, value)}
            onGoToPlan={scrollToPlan}
          />
        )}

        {rowsPage && rowsPage.total > PAGE_SIZE && (
          <div className="imports-review__pager">
            <button type="button" className="btn btn--ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              {t("imports.review.prevPage")}
            </button>
            <span className="muted">
              {t("imports.review.pageOf", {
                from: (page - 1) * PAGE_SIZE + 1,
                to: Math.min(page * PAGE_SIZE, rowsPage.total),
                total: rowsPage.total,
              })}
            </span>
            <button
              type="button"
              className="btn btn--ghost"
              disabled={page * PAGE_SIZE >= rowsPage.total}
              onClick={() => setPage((p) => p + 1)}
            >
              {t("imports.review.nextPage")}
            </button>
          </div>
        )}
      </div>

      {counts && (
        <SummaryPanel
          batch={batch}
          counts={counts}
          mergedCount={mergedCount}
          strategy={strategy}
          onStrategyChange={setStrategy}
          atomicity={atomicity}
          onAtomicityChange={setAtomicity}
          continueAfterErrors={continueAfterErrors}
          onContinueAfterErrorsChange={setContinueAfterErrors}
          onAutofix={() => void onOpenAutofix()}
          autofixCount={counts.error > 0 ? counts.error : 0}
          onImport={() => void onImport()}
          importing={importing}
          planPending={planPending}
        />
      )}

      {autofixFixes && (
        <AutofixModal
          fixes={autofixFixes}
          selected={autofixSelected}
          onToggle={(key) =>
            setAutofixSelected((s) => {
              const next = new Set(s);
              if (next.has(key)) next.delete(key);
              else next.add(key);
              return next;
            })
          }
          applying={autofixApplying}
          onApply={() => void onApplyAutofix()}
          onClose={() => setAutofixFixes(null)}
        />
      )}
    </div>
  );
}
