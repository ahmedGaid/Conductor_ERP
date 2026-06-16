import { useState } from "react";
import { useTranslation } from "react-i18next";

import { balanceSheet, type StatementLine } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ExportButtons } from "../../components/ExportButtons";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

export function BalanceSheetPage() {
  const { t } = useTranslation();
  const [asOf, setAsOf] = useState("");
  const { data, loading, error } = useAsync(() => balanceSheet(asOf || undefined), [asOf]);

  return (
    <section className="acct-page">
      <h1>{t("nav.accounting")}</h1>
      <AccountingNav />

      <div className="acct-toolbar">
        <label className="acct-field">
          <span>{t("accounting.report.asOf")}</span>
          <input type="date" className="latin" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
        </label>
        {data && (
          <span className={data.is_balanced ? "acct-balanced" : "acct-unbalanced"}>
            {data.is_balanced ? t("accounting.entry.balanced") : t("accounting.entry.unbalanced")}
          </span>
        )}
      </div>

      {loading && <p className="muted">{t("common.loading")}</p>}
      {error && <p className="error-text">{error}</p>}

      {data && <ExportButtons path={`/accounting/reports/balance-sheet${asOf ? `?as_of=${asOf}` : ""}`} />}

      {data && (
        <div className="stmt-grid">
          <Section title={t("accounting.stmt.assets")} lines={data.assets} total={data.total_assets} totalLabel={t("accounting.stmt.totalAssets")} />
          <div className="stmt-col">
            <Section title={t("accounting.stmt.liabilities")} lines={data.liabilities} total={data.total_liabilities} totalLabel={t("accounting.stmt.totalLiabilities")} />
            <Section
              title={t("accounting.stmt.equity")}
              lines={[...data.equity, { account_code: "—", account_name: t("accounting.stmt.netIncome"), amount: data.net_income }]}
              total={data.total_equity + data.net_income}
              totalLabel={t("accounting.stmt.totalEquity")}
            />
            <div className="card stmt__net">
              <span>{t("accounting.stmt.totalLiabEquity")}</span>
              <span><Bdi>{formatMinor(data.total_liabilities_and_equity)}</Bdi></span>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function Section({ title, lines, total, totalLabel }: { title: string; lines: StatementLine[]; total: number; totalLabel: string }) {
  return (
    <div className="card stmt__section">
      <h2 className="stmt__section-title">{title}</h2>
      <table className="acct-table">
        <tbody>
          {lines.map((l, i) => (
            <tr key={`${l.account_code}-${i}`}>
              <td>{l.account_code !== "—" ? <><Bdi>{l.account_code}</Bdi> · </> : null}{l.account_name}</td>
              <td className="acct-table__num"><Bdi>{formatMinor(l.amount)}</Bdi></td>
            </tr>
          ))}
          {lines.length === 0 && <tr><td className="muted" colSpan={2}>—</td></tr>}
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
