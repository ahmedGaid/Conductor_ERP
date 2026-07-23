import { useTranslation } from "react-i18next";

import type { ImportBatch } from "../../api/smartImports";

const STRATEGIES = ["create_only", "update_only", "upsert", "skip_existing"] as const;
type Strategy = (typeof STRATEGIES)[number];

export interface ReviewCounts {
  all: number;
  valid: number;
  error: number;
  duplicate: number;
  skipped: number;
}

function entityLabel(t: (k: string, o?: Record<string, unknown>) => string, entity: string): string {
  return t(`imports.entity.${entity.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase())}`, { defaultValue: entity });
}

export function SummaryPanel({
  batch,
  counts,
  mergedCount,
  strategy,
  onStrategyChange,
  atomicity,
  onAtomicityChange,
  continueAfterErrors,
  onContinueAfterErrorsChange,
  onAutofix,
  autofixCount,
  onImport,
  importing,
  planPending,
}: {
  batch: ImportBatch;
  counts: ReviewCounts;
  mergedCount: number;
  strategy: Strategy;
  onStrategyChange: (s: Strategy) => void;
  atomicity: boolean;
  onAtomicityChange: (v: boolean) => void;
  continueAfterErrors: boolean;
  onContinueAfterErrorsChange: (v: boolean) => void;
  onAutofix: () => void;
  autofixCount: number | null;
  onImport: () => void;
  importing: boolean;
  planPending: number;
}) {
  const { t } = useTranslation();

  // "Create N, update M, skip K" reads off the CURRENT strategy + counts, not a server round trip.
  // `mergedCount` is the rows this session's own duplicate decisions turned into updates — a
  // session-scoped tally (a resumed/reloaded review starts it at 0), the honest number we have
  // without a dedicated backend aggregate; the exact row-by-row plan is what the row list already
  // shows. An undecided duplicate defaults to skipped at execute time (`validate.execute_status`).
  const willSkip = counts.error + counts.skipped + (counts.duplicate - mergedCount);
  const willCreate = strategy === "update_only" ? 0 : counts.valid;
  const willUpdate = strategy === "create_only" ? 0 : mergedCount;
  const canImport = planPending === 0 && !importing && counts.all > 0;

  return (
    <aside className="imports-summary card">
      <div className="imports-summary__row">
        <h2 className="imports-summary__title">{t("imports.summary.title")}</h2>
        {autofixCount !== null && autofixCount > 0 && (
          <button type="button" className="btn btn--ghost" onClick={onAutofix}>
            {t("imports.autofix.trigger", { count: autofixCount })}
          </button>
        )}
      </div>

      <fieldset className="imports-summary__strategy">
        <legend className="muted">{t("imports.summary.strategyLabel")}</legend>
        {STRATEGIES.map((s) => (
          <label key={s} className="imports-summary__strategy-opt">
            <input type="radio" name="import-strategy" value={s} checked={strategy === s} onChange={() => onStrategyChange(s)} />
            <span>
              <span className="imports-summary__strategy-name">{t(`imports.summary.strategy.${s}.name`)}</span>
              <span className="imports-summary__strategy-desc muted">{t(`imports.summary.strategy.${s}.desc`)}</span>
            </span>
          </label>
        ))}
      </fieldset>

      <div className="imports-summary__toggles">
        <label className="imports-summary__toggle">
          <input type="checkbox" checked={atomicity} onChange={(e) => onAtomicityChange(e.target.checked)} />
          {t("imports.summary.atomicity")}
        </label>
        <label className="imports-summary__toggle">
          <input
            type="checkbox"
            checked={continueAfterErrors}
            onChange={(e) => onContinueAfterErrorsChange(e.target.checked)}
          />
          {t("imports.summary.continueAfterErrors")}
        </label>
      </div>

      {planPending > 0 && (
        <p className="imports-summary__notice" role="status">
          {t("imports.summary.planPending", { count: planPending })}
        </p>
      )}

      <button type="button" className="btn btn--primary imports-summary__cta" disabled={!canImport} onClick={onImport}>
        {importing
          ? t("common.loading")
          : t("imports.summary.importCta", {
              create: willCreate,
              update: willUpdate,
              skip: willSkip,
              entity: entityLabel(t, batch.entity),
            })}
      </button>
    </aside>
  );
}
