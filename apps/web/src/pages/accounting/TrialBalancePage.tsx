import { useState } from "react";
import { useTranslation } from "react-i18next";

import { listPeriods, trialBalance } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ExportButtons } from "../../components/ExportButtons";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

export function TrialBalancePage() {
  const { t } = useTranslation();
  const [period, setPeriod] = useState("");
  const { data: periods } = useAsync(listPeriods, [], "accounting:periods");
  const { data, loading, error } = useAsync(() => trialBalance(period || undefined), [period]);

  return (
    <section className="acct-page">
      <AccountingNav />

      <div className="acct-toolbar">
        <label className="acct-field">
          <span>{t("accounting.report.period")}</span>
          <select className="latin" value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="">{t("accounting.report.allPeriods")}</option>
            {(periods ?? []).map((p) => (
              <option key={p.code} value={p.code}>
                {p.code}
              </option>
            ))}
          </select>
        </label>
        {data && (
          <span className={data.is_balanced ? "acct-balanced" : "acct-unbalanced"}>
            {data.is_balanced ? t("accounting.entry.balanced") : t("accounting.entry.unbalanced")}
          </span>
        )}
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
      {error && <p className="error-text">{error}</p>}

      {data && <ExportButtons path={`/accounting/reports/trial-balance${period ? `?period=${period}` : ""}`} />}

      {data && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.account.code")}</th>
                <th>{t("accounting.account.name")}</th>
                <th className="acct-table__num">{t("accounting.entry.debit")}</th>
                <th className="acct-table__num">{t("accounting.entry.credit")}</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.account_code}>
                  <td><Bdi>{r.account_code}</Bdi></td>
                  <td>{r.account_name}</td>
                  <td className="acct-table__num"><Bdi>{formatMinor(r.debit)}</Bdi></td>
                  <td className="acct-table__num"><Bdi>{formatMinor(r.credit)}</Bdi></td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={2}>{t("accounting.entry.totals")}</td>
                <td className="acct-table__num"><Bdi>{formatMinor(data.total_debit)}</Bdi></td>
                <td className="acct-table__num"><Bdi>{formatMinor(data.total_credit)}</Bdi></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </section>
  );
}
