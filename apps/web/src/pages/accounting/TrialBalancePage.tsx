import { useState } from "react";
import { useTranslation } from "react-i18next";

import { listPeriods, trialBalance } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { formatMoneyNumeral } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { useReportPageActions } from "../../hooks/useReportPageActions";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import { ComboBox } from "../../components/ComboBox";
import "./accounting.css";

export function TrialBalancePage() {
  const { t } = useTranslation();
  const [period, setPeriod] = useState("");
  const { data: periods } = useAsync(listPeriods, [], "accounting:periods");
  const { data, loading, error, reload } = useAsync(() => trialBalance(period || undefined), [period]);

  useReportPageActions(data ? `/accounting/reports/trial-balance${period ? `?period=${period}` : ""}` : null);

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
        {data && (
          <span className={data.is_balanced ? "acct-balanced" : "acct-unbalanced"}>
            {data.is_balanced ? t("accounting.entry.balanced") : t("accounting.entry.unbalanced")}
          </span>
        )}
      </div>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.account.code")}</th>
                <th>{t("accounting.account.name")}</th>
                <th className="acct-table__num">{t("accounting.entry.debit")} (EGP)</th>
                <th className="acct-table__num">{t("accounting.entry.credit")} (EGP)</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.account_code}>
                  <td><Bdi>{r.account_code}</Bdi></td>
                  <td>{r.account_name}</td>
                  <td className="acct-table__num"><Bdi>{formatMoneyNumeral(r.debit)}</Bdi></td>
                  <td className="acct-table__num"><Bdi>{formatMoneyNumeral(r.credit)}</Bdi></td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={2}>{t("accounting.entry.totals")}</td>
                <td className="acct-table__num"><Bdi>{formatMoneyNumeral(data.total_debit)}</Bdi></td>
                <td className="acct-table__num"><Bdi>{formatMoneyNumeral(data.total_credit)}</Bdi></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </section>
  );
}
