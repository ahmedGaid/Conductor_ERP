import { useState } from "react";
import { useTranslation } from "react-i18next";

import { incomeStatement, listCostCenters, listPeriods, type StatementLine } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ExportButtons } from "../../components/ExportButtons";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

export function IncomeStatementPage() {
  const { t } = useTranslation();
  const [period, setPeriod] = useState("");
  const [costCenter, setCostCenter] = useState("");
  const { data: periods } = useAsync(listPeriods, [], "accounting:periods");
  const { data: costCenters } = useAsync(listCostCenters, [], "accounting:cost-centers");
  const { data, loading, error, reload } = useAsync(
    () => incomeStatement({ ...(period ? { period } : {}), ...(costCenter ? { cost_center: costCenter } : {}) }),
    [period, costCenter],
  );

  const exportQuery = new URLSearchParams();
  if (period) exportQuery.set("period", period);
  if (costCenter) exportQuery.set("cost_center", costCenter);
  const exportSuffix = exportQuery.toString() ? `?${exportQuery.toString()}` : "";

  return (
    <section className="acct-page">
      <AccountingNav />

      <div className="acct-toolbar">
        <label className="acct-field">
          <span>{t("accounting.report.period")}</span>
          <select className="latin" value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="">{t("accounting.report.allPeriods")}</option>
            {(periods ?? []).map((p) => (
              <option key={p.code} value={p.code}>{p.code}</option>
            ))}
          </select>
        </label>
        <label className="acct-field">
          <span>{t("accounting.costCenters.label")}</span>
          <select className="latin" value={costCenter} onChange={(e) => setCostCenter(e.target.value)}>
            <option value="">{t("accounting.costCenters.all")}</option>
            {(costCenters ?? []).filter((c) => c.is_active).map((c) => (
              <option key={c.code} value={c.code}>{c.code} · {c.name}</option>
            ))}
          </select>
        </label>
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

      {data && <ExportButtons path={`/accounting/reports/income-statement${exportSuffix}`} />}

      {data && (
        <div className="card stmt">
          <Section title={t("accounting.types.income")} lines={data.revenue} total={data.total_revenue} totalLabel={t("accounting.stmt.totalRevenue")} />
          <Section title={t("accounting.types.expense")} lines={data.expenses} total={data.total_expenses} totalLabel={t("accounting.stmt.totalExpenses")} />
          <div className="stmt__net">
            <span>{t("accounting.stmt.netIncome")}</span>
            <span className={data.net_income >= 0 ? "acct-balanced" : "acct-unbalanced"}>
              <Bdi>{formatMinor(data.net_income)}</Bdi>
            </span>
          </div>
        </div>
      )}
    </section>
  );
}

function Section({ title, lines, total, totalLabel }: { title: string; lines: StatementLine[]; total: number; totalLabel: string }) {
  return (
    <div className="stmt__section">
      <h2 className="stmt__section-title">{title}</h2>
      <table className="acct-table">
        <tbody>
          {lines.map((l) => (
            <tr key={l.account_code}>
              <td><Bdi>{l.account_code}</Bdi> · {l.account_name}</td>
              <td className="acct-table__num"><Bdi>{formatMinor(l.amount)}</Bdi></td>
            </tr>
          ))}
          {lines.length === 0 && (
            <tr><td className="muted" colSpan={2}>—</td></tr>
          )}
        </tbody>
        <tfoot>
          <tr>
            <td>{totalLabel}</td>
            <td className="acct-table__num"><Bdi>{formatMinor(total)}</Bdi></td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
