import { useState } from "react";
import { useTranslation } from "react-i18next";

import { generalLedger, listAccounts } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

export function GeneralLedgerPage() {
  const { t } = useTranslation();
  const { data: accounts } = useAsync(listAccounts, []);
  const postable = (accounts ?? []).filter((a) => a.is_postable);
  const [account, setAccount] = useState("");

  const { data, loading, error } = useAsync(
    () => (account ? generalLedger(account) : Promise.resolve(null)),
    [account],
  );

  return (
    <section className="acct-page">
      <h1>{t("nav.accounting")}</h1>
      <AccountingNav />

      <div className="acct-toolbar">
        <label className="acct-field">
          <span>{t("accounting.entry.account")}</span>
          <select value={account} onChange={(e) => setAccount(e.target.value)}>
            <option value="">{t("accounting.report.pickAccount")}</option>
            {postable.map((a) => (
              <option key={a.code} value={a.code}>
                {a.code} · {a.name}
              </option>
            ))}
          </select>
        </label>
        {data && (
          <span className="muted">
            {t("accounting.report.closing")}: <Bdi>{formatMinor(data.closing_balance)}</Bdi>
          </span>
        )}
      </div>

      {loading && <p className="muted">{t("common.loading")}</p>}
      {error && <p className="error-text">{error}</p>}
      {!account && <p className="muted">{t("accounting.report.pickAccount")}</p>}

      {data && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.entry.date")}</th>
                <th>{t("accounting.journals.number")}</th>
                <th>{t("accounting.entry.memo")}</th>
                <th className="acct-table__num">{t("accounting.entry.debit")}</th>
                <th className="acct-table__num">{t("accounting.entry.credit")}</th>
                <th className="acct-table__num">{t("accounting.report.running")}</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((l, i) => (
                <tr key={i}>
                  <td className="latin">{l.date}</td>
                  <td className="latin">{l.entry_number}</td>
                  <td>{l.memo}</td>
                  <td className="acct-table__num"><Bdi>{l.debit ? formatMinor(l.debit) : ""}</Bdi></td>
                  <td className="acct-table__num"><Bdi>{l.credit ? formatMinor(l.credit) : ""}</Bdi></td>
                  <td className="acct-table__num"><Bdi>{formatMinor(l.running_balance)}</Bdi></td>
                </tr>
              ))}
              {data.lines.length === 0 && (
                <tr>
                  <td colSpan={6} className="muted">{t("accounting.report.noActivity")}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
