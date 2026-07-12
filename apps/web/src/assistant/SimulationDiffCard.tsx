import { useTranslation } from "react-i18next";

import type { SimulationDiff } from "../api/assistant";
import { NavIcon } from "../app/icons";
import { Bdi } from "../components/Bdi";
import { formatMinor } from "../lib/money";

// Each created entity's home-module icon — chrome stays monochrome, the icon only names the area.
const CREATE_ICON: Record<string, string> = {
  customer: "crm",
  sales_order: "sales",
  stock_transfer: "inventory",
  journal_entry: "accounting",
};

interface SimulationDiffCardProps {
  // The parent owns the request (a card triggers it from a proposal); the three states are passed in
  // so this component is a pure render — reusable by Phase A/B's preview surfaces the same way.
  loading?: boolean;
  error?: string | null;
  diff?: SimulationDiff | null;
}

/**
 * The dry-run diff — "see it before it happens". Nothing here was written; every number is what the
 * plan WOULD do if confirmed. Monochrome chrome; the only colour is a failed step (danger) or a
 * money delta, always paired with a word/icon (per brand). Designed loading / error / empty states.
 */
export function SimulationDiffCard({ loading, error, diff }: SimulationDiffCardProps) {
  const { t } = useTranslation();

  // --- loading: a settled skeleton, never a bare "Loading…" ------------------------------------
  if (loading) {
    return (
      <div className="sim-card sim-card--loading" aria-busy="true" aria-live="polite">
        <span className="sim-card__spark" aria-hidden="true">
          <NavIcon name="sparkle" />
        </span>
        <span className="sim-card__loading-line">{t("assistant.simulation.running")}</span>
      </div>
    );
  }

  // --- error: the honest, blame-free failure line ----------------------------------------------
  if (error) {
    return (
      <div className="sim-card sim-card--error" dir="auto">
        <NavIcon name="flag" />
        <span>{error}</span>
      </div>
    );
  }

  // --- empty guard: a plan with no steps never renders a bare card ------------------------------
  if (!diff || diff.steps.length === 0) return null;

  const creates = Object.entries(diff.creates).filter(([, n]) => n > 0);
  const money = [
    { key: "receivables", minor: diff.money.receivables_delta_minor },
    { key: "payables", minor: diff.money.payables_delta_minor },
    // Debit == credit for a balanced entry; one "posted to the ledger" line is enough.
    { key: "gl", minor: diff.gl.debit_delta_minor },
  ].filter((m) => m.minor !== 0);
  const failed = diff.steps.find((s) => !s.ok);

  return (
    <div className="sim-card" dir="auto">
      <header className="sim-card__head">
        <span className="sim-card__spark" aria-hidden="true">
          <NavIcon name="sparkle" />
        </span>
        <span className="sim-card__title">{t("assistant.simulation.title")}</span>
      </header>

      {/* What the plan would create — the headline of the impact. */}
      {creates.length > 0 && (
        <ul className="sim-card__creates">
          {creates.map(([entity, count]) => (
            <li key={entity} className="sim-card__create">
              <NavIcon name={CREATE_ICON[entity] ?? "sparkle"} />
              {t(`assistant.simulation.creates.${entity}`, {
                count,
                defaultValue: `{{count}} ${entity}`,
              })}
            </li>
          ))}
        </ul>
      )}

      {/* Money it would move — only the non-zero deltas, each a word + a tabular amount. */}
      {money.length > 0 && (
        <ul className="sim-card__money">
          {money.map((m) => (
            <li key={m.key} className="sim-card__money-row">
              <span className="sim-card__money-label">
                {t(`assistant.simulation.money.${m.key}`)}
              </span>
              <span className="num sim-card__money-value">
                <Bdi>{formatMinor(m.minor)}</Bdi>
              </span>
            </li>
          ))}
        </ul>
      )}

      {/* Every step, ticked or flagged, with its verifier verdict when the action declared one. */}
      <ul className="sim-card__steps">
        {diff.steps.map((step, i) => (
          <li
            key={i}
            className={`sim-card__step${step.ok ? "" : " sim-card__step--bad"}`}
            dir="auto"
          >
            <NavIcon name={step.ok ? "check" : "flag"} />
            <span className="sim-card__step-text">
              {step.summary ?? t(`assistant.action.titles.${step.action}`, step.action)}
              {step.ok && step.verifier && step.verifier.packs.length > 0 && (
                <span className="sim-card__verified">
                  {t("assistant.simulation.verified", { count: step.verifier.packs.length })}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>

      {/* A stopped plan: reassure that the preview changed nothing. */}
      {failed ? (
        <p className="sim-card__nothing" dir="auto">
          <NavIcon name="info" />
          {t("assistant.simulation.nothingWritten")}
        </p>
      ) : (
        <p className="sim-card__safe" dir="auto">
          {t("assistant.simulation.previewOnly")}
        </p>
      )}
    </div>
  );
}
