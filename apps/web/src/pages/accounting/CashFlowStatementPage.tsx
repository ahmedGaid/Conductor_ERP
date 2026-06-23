import { useState } from "react";
import { useTranslation } from "react-i18next";

import { cashFlow, listPeriods } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ExportButtons } from "../../components/ExportButtons";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./accounting.css";

export function CashFlowStatementPage() {
  const { t } = useTranslation();
  const [period, setPeriod] = useState("");
  const { data: periods } = useAsync(listPeriods, [], "accounting:periods");
  const { data, loading, error, reload } = useAsync(() => cashFlow(period ? { period } : {}), [period]);

  const rows: { label: string; value: number; strong?: boolean }[] = data
    ? [
        { label: t("accounting.stmt.opening"), value: data.opening_balance },
        { label: t("dashboard.cashIn"), value: data.cash_in },
        { label: t("dashboard.cashOut"), value: -data.cash_out },
        { label: t("accounting.stmt.netChange"), value: data.net_change, strong: true },
        { label: t("accounting.report.closing"), value: data.closing_balance, strong: true },
      ]
    : [];

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
        {data && (
          <span className={data.reconciles ? "acct-balanced" : "acct-unbalanced"}>
            {data.reconciles ? t("accounting.stmt.reconciled") : t("accounting.stmt.notReconciled")}
          </span>
        )}
      </div>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && <ExportButtons path={`/accounting/reports/cash-flow${period ? `?period=${period}` : ""}`} />}

      {data && (
        <div className="card stmt">
          <table className="acct-table">
            <tbody>
              {rows.map((r) => (
                <tr key={r.label}>
                  <td className={r.strong ? "stmt__strong" : ""}>{r.label}</td>
                  <td className={`acct-table__num ${r.strong ? "stmt__strong" : ""}`}>
                    <Bdi>{formatMinor(r.value)}</Bdi>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
