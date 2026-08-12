import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  getOpsSummary,
  listOpsTraces,
  type OpsSummary,
  type OpsTrace,
} from "../../api/assistantOps";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { StatCard } from "../../components/StatCard";
import { ComboBox } from "../../components/ComboBox";
import { useAsync } from "../../hooks/useAsync";
import { formatMicrocentsUsd } from "../../lib/money";
import "./ops.css";

const DAY_OPTIONS = [7, 14, 30];
const PAGE_SIZE = 20;
const FEATURES = ["chat", "ask", "agent", "extract", "digest", "suggest", "embed", "eval"];
const STATUSES = ["ok", "error", "timeout", "cancelled", "guardrail_blocked"];

function DayBars({ daily }: { daily: OpsSummary["daily"] }) {
  const max = Math.max(1, ...daily.map((d) => d.count));
  return (
    <div className="ops-bars">
      {daily.map((d) => (
        <div key={d.date} className="ops-bars__col">
          <span className="ops-bars__count latin muted">{d.count}</span>
          <div className="ops-bars__track">
            <div className="ops-bars__fill" style={{ blockSize: `${(d.count / max) * 100}%` }} />
          </div>
          <span className="ops-bars__label latin muted">{d.date.slice(5)}</span>
        </div>
      ))}
    </div>
  );
}

function TraceRow({ trace, expanded, onToggle }: {
  trace: OpsTrace;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { t } = useTranslation();
  return (
    <>
      <tr className="ops-trace-row" onClick={onToggle}>
        <td className="latin muted">{trace.created_at.replace("T", " ").slice(0, 16)}</td>
        <td>{t(`ops.feature.${trace.feature}`)}</td>
        <td className="latin">{trace.actor?.username ?? "—"}</td>
        <td className="latin muted">{trace.provider}/{trace.model || "—"}</td>
        <td>
          <span className={`kpill kpill--${trace.status === "ok" ? "ready" : "failed"}`}>
            {t(`ops.status.${trace.status}`)}
          </span>
        </td>
        <td className="latin muted">{trace.latency_ms}ms</td>
        <td className="latin muted"><Bdi>{formatMicrocentsUsd(trace.cost_microcents)}</Bdi></td>
        <td className="latin muted">{trace.steps.length}</td>
      </tr>
      {expanded &&
        (trace.steps.length > 0 ||
          (trace.meta.routing?.skipped.length ?? 0) > 0 ||
          (trace.meta.plan?.length ?? 0) > 0 ||
          !!trace.meta.plan_fallback) && (
        <tr className="ops-trace-row__detail">
          <td colSpan={8}>
            {/* T5.2: what the typed planner decided for this run — the ordered steps it committed
                to, or the reason it handed the turn back to the reactive loop. */}
            {trace.meta.plan && trace.meta.plan.length > 0 && (
              <ol className="ops-plan" aria-label={t("ops.plan.title")}>
                {trace.meta.plan.map((s, i) => (
                  <li key={i}>
                    <span className="latin">{s.tool}</span>
                    <span className="muted"> — {s.why}</span>
                  </li>
                ))}
              </ol>
            )}
            {trace.meta.plan_fallback && (
              <p className="ops-routing-skipped muted">
                {t("ops.plan.fallback", { reason: trace.meta.plan_fallback })}
              </p>
            )}
            {trace.meta.routing && trace.meta.routing.skipped.length > 0 && (
              <p className="ops-routing-skipped muted latin">
                {t("ops.routing.skipped")}:{" "}
                {trace.meta.routing.skipped
                  .map((s) => `${s.provider} (${s.reason.replace(/_/g, " ")})`)
                  .join(", ")}
              </p>
            )}
            {trace.steps.length > 0 && (
              <table className="ops-step-table">
                <thead>
                  <tr>
                    <th>{t("ops.step.seq")}</th>
                    <th>{t("ops.step.kind")}</th>
                    <th>{t("ops.step.name")}</th>
                    <th>{t("ops.step.latency")}</th>
                    <th>{t("ops.step.status")}</th>
                  </tr>
                </thead>
                <tbody>
                  {trace.steps.map((s) => (
                    <tr key={s.seq}>
                      <td className="latin muted">{s.seq}</td>
                      <td>{t(`ops.stepKind.${s.kind}`)}</td>
                      <td className="latin">{s.name || "—"}</td>
                      <td className="latin muted">{s.latency_ms}ms</td>
                      <td>
                        <span className={`kpill kpill--${s.ok ? "ready" : "failed"}`}>
                          {s.ok ? t("ops.status.ok") : t("ops.status.error")}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

// Admin-only ops surface (ai-reliability T1.8): answers "what did the AI do today, what did it
// cost, is it healthy" from the traces the tracing seam (services/tracing.py) already writes for
// every provider call — no separate telemetry pipeline, same customer-hosted DB.
export function OpsPage() {
  const { t } = useTranslation();
  const [days, setDays] = useState(7);
  const [feature, setFeature] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const summary = useAsync(() => getOpsSummary(days), [days]);
  const traces = useAsync(
    () => listOpsTraces({ days, feature: feature || undefined, status: status || undefined,
                          page, page_size: PAGE_SIZE }),
    [days, feature, status, page],
  );

  function resetToFirstPage<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v);
      setPage(1);
      setExpandedId(null);
    };
  }
  const onFeature = resetToFirstPage(setFeature);
  const onStatus = resetToFirstPage(setStatus);

  const s = summary.data;
  const tp = traces.data;
  const totalPages = tp ? Math.max(1, Math.ceil(tp.count / tp.page_size)) : 1;

  return (
    <section className="page-enter">
      <header className="module-head">
        <h1 className="module-head__title">{t("ops.title")}</h1>
        <p className="module-head__desc">{t("ops.subtitle")}</p>
      </header>

      <div className="ops-days">
        {DAY_OPTIONS.map((d) => (
          <button
            key={d}
            type="button"
            className={d === days ? "btn btn--sm btn--primary" : "btn btn--sm"}
            onClick={() => { setDays(d); setPage(1); setExpandedId(null); }}
          >
            {t("ops.daysOption", { n: d })}
          </button>
        ))}
      </div>

      {summary.loading && <ListSkeleton rows={2} />}
      {summary.error && <ErrorState message={summary.error} onRetry={summary.reload} />}

      {s && (
        <>
          <div className="ops-tiles">
            <StatCard label={t("ops.totalCalls")} value={String(s.total_calls)} icon="sparkle" />
            <StatCard
              label={t("ops.errorRate")}
              value={`${(s.error_rate * 100).toFixed(1)}%`}
              icon="trendDown"
              invertDelta
            />
            <StatCard
              label={t("ops.latency")}
              value={`${s.latency_ms.p50}ms / ${s.latency_ms.p95}ms`}
              hint={t("ops.p50p95")}
              icon="clock"
            />
            <StatCard
              label={t("ops.tokens")}
              value={`${s.input_tokens.toLocaleString("en-US")} / ${s.output_tokens.toLocaleString("en-US")}`}
              hint={t("ops.inOut")}
              icon="reports"
            />
            <StatCard label={t("ops.cost")} value={formatMicrocentsUsd(s.cost_microcents)} icon="accounting" />
          </div>

          <div className="ops-row">
            <div className="card ops-chart-card">
              <h2 className="ops-card__title">{t("ops.callsPerDay")}</h2>
              {s.daily.length > 0 ? (
                <DayBars daily={s.daily} />
              ) : (
                <p className="ops-card__empty">{t("ops.empty.title")}</p>
              )}
            </div>

            <div className="card ops-side-card">
              <h2 className="ops-card__title">{t("ops.topErrors")}</h2>
              {s.top_error_classes.length === 0 ? (
                <p className="ops-card__empty">{t("ops.noErrors")}</p>
              ) : (
                <ul className="ops-error-list">
                  {s.top_error_classes.map((e) => (
                    <li key={e.error_class}>
                      <span className="latin">{e.error_class}</span>
                      <span className="latin muted">{e.count}</span>
                    </li>
                  ))}
                </ul>
              )}

              <h2 className="ops-card__title ops-card__title--spaced">{t("ops.budgets.title")}</h2>
              <ul className="ops-error-list">
                {s.budgets.map((b) => (
                  <li key={b.scope}>
                    <span>{t(`ops.budgets.scope.${b.scope}`)}</span>
                    <span className="latin muted">
                      {b.limit_microcents == null ? (
                        t("ops.budgets.unconfigured")
                      ) : (
                        <>
                          <Bdi>{b.spend_microcents == null ? "—" : formatMicrocentsUsd(b.spend_microcents)}</Bdi>
                          {" / "}
                          <Bdi>{formatMicrocentsUsd(b.limit_microcents)}</Bdi>
                        </>
                      )}
                    </span>
                  </li>
                ))}
              </ul>

              <h2 className="ops-card__title ops-card__title--spaced">{t("ops.evalScoreboard")}</h2>
              {s.eval_scoreboard ? (
                <div className="ops-eval">
                  <Bdi>
                    <span className="ops-eval__rate">
                      {((s.eval_scoreboard.pass_rate ?? 0) * 100).toFixed(0)}%
                    </span>
                  </Bdi>
                  <span className="ops-card__hint latin muted">{s.eval_scoreboard.date}</span>
                </div>
              ) : (
                <p className="ops-card__empty">{t("ops.noEvals")}</p>
              )}
            </div>
          </div>
        </>
      )}

      <div className="ops-filters">
        <ComboBox
          value={feature}
          onChange={onFeature}
          placeholder={t("ops.allFeatures")}
          options={[{ value: "", label: t("ops.allFeatures") }, ...FEATURES.map((f) => ({ value: f, label: t(`ops.feature.${f}`) }))]}
          aria-label={t("ops.filterFeature")}
        />
        <select value={status} onChange={(e) => onStatus(e.target.value)} aria-label={t("ops.filterStatus")}>
          <option value="">{t("ops.allStatuses")}</option>
          {STATUSES.map((st) => (
            <option key={st} value={st}>{t(`ops.status.${st}`)}</option>
          ))}
        </select>
      </div>

      {traces.loading && <ListSkeleton rows={4} />}
      {traces.error && <ErrorState message={traces.error} onRetry={traces.reload} />}
      {tp && tp.results.length === 0 && !traces.loading && (
        <EmptyState title={t("ops.empty.title")} hint={t("ops.empty.body")} />
      )}

      {tp && tp.results.length > 0 && (
        <>
          <div className="card ops-table-wrap">
            <table className="ops-trace-table">
              <thead>
                <tr>
                  <th>{t("ops.col.time")}</th>
                  <th>{t("ops.col.feature")}</th>
                  <th>{t("ops.col.actor")}</th>
                  <th>{t("ops.col.model")}</th>
                  <th>{t("ops.col.status")}</th>
                  <th>{t("ops.col.latency")}</th>
                  <th>{t("ops.col.cost")}</th>
                  <th>{t("ops.col.steps")}</th>
                </tr>
              </thead>
              <tbody>
                {tp.results.map((tr) => (
                  <TraceRow
                    key={tr.id}
                    trace={tr}
                    expanded={expandedId === tr.id}
                    onToggle={() => setExpandedId(expandedId === tr.id ? null : tr.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>

          <div className="ops-pagination">
            <button type="button" className="btn btn--sm" disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}>
              {t("ops.prevPage")}
            </button>
            <span className="latin muted">{page} / {totalPages}</span>
            <button type="button" className="btn btn--sm" disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}>
              {t("ops.nextPage")}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
