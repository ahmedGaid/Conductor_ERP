import { useMemo, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import {
  getAssistantUsage,
  type UsageBudgetScope,
  type UsageMonth,
} from "../../api/assistantUsage";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { StatCard } from "../../components/StatCard";
import { useAsync } from "../../hooks/useAsync";
import { formatMicrocentsUsd } from "../../lib/money";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import "./settings.css";
import "./aiUsage.css";

function currentMonth(): string {
  return new Date().toISOString().slice(0, 7);
}

function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + delta, 1));
  return d.toISOString().slice(0, 7);
}

function monthLabel(month: string, locale: string): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1, 1));
  return new Intl.DateTimeFormat(`${locale}-u-nu-latn`, { month: "long", year: "numeric", timeZone: "UTC" }).format(d);
}

function BudgetRow({ label, scope, consumedMicrocents }: {
  label: string;
  scope: UsageBudgetScope;
  consumedMicrocents?: number;
}) {
  const { t } = useTranslation();
  if (scope.limit_microcents === null) {
    return (
      <div className="setrow">
        <span className="setrow__label"><span className="setrow__title">{label}</span></span>
        <span className="setrow__control muted">{t("settings.aiUsage.budget.notConfigured")}</span>
      </div>
    );
  }

  const actionWord = t(`settings.aiUsage.budget.action.${scope.action}`);
  if (consumedMicrocents === undefined) {
    return (
      <div className="setrow">
        <span className="setrow__label">
          <span className="setrow__title">{label}</span>
          <span className="setrow__desc">{actionWord}</span>
        </span>
        <span className="setrow__control latin"><Bdi>{formatMicrocentsUsd(scope.limit_microcents)}</Bdi></span>
      </div>
    );
  }

  const pct = Math.min(999, Math.round((consumedMicrocents / scope.limit_microcents) * 100));
  const tone = pct >= 100 ? "over" : pct >= 80 ? "warning" : "ok";

  return (
    <div className="setrow setrow--block">
      <span className="setrow__label">
        <span className="setrow__title">{label}</span>
        <span className="setrow__desc">{actionWord}</span>
      </span>
      <div className="usage-budget">
        <div className="usage-budget__track">
          <div className={`usage-budget__fill usage-budget__fill--${tone}`} style={{ inlineSize: `${Math.min(100, pct)}%` }} />
        </div>
        <span className={`usage-budget__figures usage-budget__figures--${tone} latin`}>
          <Trans
            i18nKey="settings.aiUsage.budget.consumedOfLimit"
            values={{
              consumed: formatMicrocentsUsd(consumedMicrocents),
              limit: formatMicrocentsUsd(scope.limit_microcents),
            }}
            components={[<Bdi key="consumed">{""}</Bdi>, <Bdi key="limit">{""}</Bdi>]}
          />
          {" — "}
          {t(`settings.aiUsage.budget.status.${tone}`)}
        </span>
      </div>
    </div>
  );
}

function UsageContent({ data, month, onPrev, onNext }: {
  data: UsageMonth;
  month: string;
  onPrev: () => void;
  onNext: () => void;
}) {
  const { t, i18n } = useTranslation();
  const isCurrentMonth = month >= currentMonth();
  const noUsage = data.totals.requests === 0;

  return (
    <div className="card setcard">
      <p className="setcard__lead">{t("settings.aiUsage.lead")}</p>

      <div className="usage-month">
        <button type="button" className="btn btn--sm" onClick={onPrev}>
          {t("settings.aiUsage.prevMonth")}
        </button>
        <span className="usage-month__label latin">{monthLabel(month, i18n.language)}</span>
        <button type="button" className="btn btn--sm" onClick={onNext} disabled={isCurrentMonth}>
          {t("settings.aiUsage.nextMonth")}
        </button>
      </div>

      {noUsage ? (
        <EmptyState
          title={t("settings.aiUsage.empty.title")}
          hint={t("settings.aiUsage.empty.hint")}
        />
      ) : (
        <>
          <div className="usage-tiles">
            <StatCard label={t("settings.aiUsage.totals.requests")} value={String(data.totals.requests)} icon="sparkle" hint={monthLabel(month, i18n.language)} />
            <StatCard
              label={t("settings.aiUsage.totals.tokens")}
              value={`${data.totals.input_tokens.toLocaleString("en-US")} / ${data.totals.output_tokens.toLocaleString("en-US")}`}
              icon="reports"
              hint={t("ops.inOut")}
            />
            <StatCard label={t("settings.aiUsage.totals.cost")} value={formatMicrocentsUsd(data.totals.cost_microcents)} icon="accounting" hint={monthLabel(month, i18n.language)} />
            <StatCard
              label={t("settings.aiUsage.totals.cacheHit")}
              value={`${(data.totals.cache_hit_share * 100).toFixed(0)}%`}
              icon="checkCircle"
              hint={monthLabel(month, i18n.language)}
            />
            <StatCard label={t("settings.aiUsage.totals.degradedMinutes")} value={String(data.totals.degraded_minutes)} icon="warning" hint={monthLabel(month, i18n.language)} />
          </div>

          <div className="setcard__block">
            <p className="setrow__title">{t("settings.aiUsage.budget.title")}</p>
            <BudgetRow
              label={t("settings.aiUsage.budget.org")}
              scope={data.budget.org}
              consumedMicrocents={data.budget.org.consumed_microcents}
            />
            <BudgetRow label={t("settings.aiUsage.budget.userDaily")} scope={data.budget.user_daily} />
            <BudgetRow label={t("settings.aiUsage.budget.perRequest")} scope={data.budget.request} />
          </div>

          {data.by_provider.length > 0 && (
            <div className="setcard__block">
              <p className="setrow__title">{t("settings.aiUsage.provider.title")}</p>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{t("settings.aiUsage.provider.col.provider")}</th>
                    <th>{t("settings.aiUsage.provider.col.requests")}</th>
                    <th>{t("settings.aiUsage.provider.col.tokens")}</th>
                    <th>{t("settings.aiUsage.provider.col.cost")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.by_provider.map((p) => (
                    <tr key={p.provider}>
                      <td className="latin">{p.provider}</td>
                      <td className="latin">{p.requests}</td>
                      <td className="latin">{p.input_tokens.toLocaleString("en-US")} / {p.output_tokens.toLocaleString("en-US")}</td>
                      <td className="latin"><Bdi>{formatMicrocentsUsd(p.cost_microcents)}</Bdi></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data.by_user.length > 0 && (
            <div className="setcard__block">
              <p className="setrow__title">{t("settings.aiUsage.byUser.title")}</p>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{t("settings.aiUsage.byUser.col.user")}</th>
                    <th>{t("settings.aiUsage.byUser.col.requests")}</th>
                    <th>{t("settings.aiUsage.byUser.col.tokens")}</th>
                    <th>{t("settings.aiUsage.byUser.col.cost")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.by_user.map((u) => (
                    <tr key={u.user_id}>
                      <td className="latin"><Bdi>{u.username}</Bdi></td>
                      <td className="latin">{u.requests}</td>
                      <td className="latin">{u.input_tokens.toLocaleString("en-US")} / {u.output_tokens.toLocaleString("en-US")}</td>
                      <td className="latin"><Bdi>{formatMicrocentsUsd(u.cost_microcents)}</Bdi></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <div className="setcard__block">
        <Link to="/assistant/ops" className="btn btn--sm">{t("settings.aiUsage.viewTraces")}</Link>
      </div>
    </div>
  );
}

export function AIUsagePage() {
  const [month, setMonth] = useState(currentMonth);
  const { data, loading, error, errorStatus, reload } = useAsync(
    () => getAssistantUsage(month), [month], "settings:ai-usage",
  );
  const isCurrentMonth = useMemo(() => month >= currentMonth(), [month]);

  return (
    <section className="page-enter">
      <SettingsNav />
      {loading && <SettingsSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} status={errorStatus} />}
      {data && (
        <UsageContent
          data={data}
          month={month}
          onPrev={() => setMonth((m) => shiftMonth(m, -1))}
          onNext={() => !isCurrentMonth && setMonth((m) => shiftMonth(m, 1))}
        />
      )}
    </section>
  );
}
