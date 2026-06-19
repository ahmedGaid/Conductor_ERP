import { useState } from "react";
import { useTranslation } from "react-i18next";

import { vatReturn } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ExportButtons } from "../../components/ExportButtons";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

const year = new Date().getFullYear();

export function VatReturnPage() {
  const { t } = useTranslation();
  const [from, setFrom] = useState(`${year}-01-01`);
  const [to, setTo] = useState(`${year}-12-31`);
  const { data, loading, error } = useAsync(() => vatReturn(from, to), [from, to]);

  const rows: { label: string; value: number; strong?: boolean }[] = data
    ? [
        { label: t("accounting.vat.output"), value: data.output_vat },
        { label: t("accounting.vat.reversals"), value: -data.reversals },
        { label: t("accounting.vat.input"), value: -data.input_vat },
        { label: t("accounting.vat.inputReversals"), value: data.input_reversals },
        { label: t("accounting.vat.netPayable"), value: data.net_payable, strong: true },
      ]
    : [];

  return (
    <section className="acct-page">
      <AccountingNav />

      <div className="acct-toolbar">
        <label className="acct-field">
          <span>{t("accounting.report.from")}</span>
          <input className="latin" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label className="acct-field">
          <span>{t("accounting.report.to")}</span>
          <input className="latin" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
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
      {error && <p className="error-text">{error}</p>}

      {data && <ExportButtons path={`/accounting/reports/vat-return?from=${from}&to=${to}`} />}

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
