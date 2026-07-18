import { useState } from "react";
import { useTranslation } from "react-i18next";

import { incomeStatement, listCostCenters, listPeriods, type StatementLine } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { useReportPageActions } from "../../hooks/useReportPageActions";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import { ComboBox } from "../../components/ComboBox";
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

  useReportPageActions(data ? `/accounting/reports/income-statement${exportSuffix}` : null);

  return (
    <section className="acct-page">
      <AccountingNav />

      <div className="acct-toolbar">
        <label className="acct-field">
          <span>{t("accounting.report.period")}</span>
          <ComboBox
            className="latin"
            value={period}
            onChange={setPeriod}
            placeholder={t("accounting.report.allPeriods")}
            options={[{ value: "", label: t("accounting.report.allPeriods") }, ...(periods ?? []).map((p) => ({ value: p.code, label: p.code }))]}
          />
        </label>
        <label className="acct-field">
          <span>{t("accounting.costCenters.label")}</span>
          <ComboBox
            className="latin"
            value={costCenter}
            onChange={setCostCenter}
            placeholder={t("accounting.costCenters.all")}
            options={[
              { value: "", label: t("accounting.costCenters.all") },
              ...(costCenters ?? []).filter((c) => c.is_active).map((c) => ({ value: c.code, label: `${c.code} · ${c.name}` })),
            ]}
          />
        </label>
      </div>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <div className="card stmt">
          <Section title={t("accounting.types.income")} lines={data.revenue} total={data.total_revenue} totalLabel={t("accounting.stmt.totalRevenue")} />
          <Section title={t("accounting.types.expense")} lines={data.expenses} total={data.total_expenses} totalLabel={t("accounting.stmt.totalExpenses")} />
          <div className="stmt__net">
            <span>{t("accounting.stmt.netIncome")}</span>
            <span className={`num ${data.net_income >= 0 ? "acct-balanced" : "acct-unbalanced"}`}>
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
