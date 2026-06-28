import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { generalLedger, listAccounts } from "../../api/accounting";
import { listCustomers } from "../../api/sales";
import { listSuppliers } from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { PartyLink, type PartyType } from "../../components/PartyLink";
import { ExportButtons } from "../../components/ExportButtons";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./accounting.css";

export function GeneralLedgerPage() {
  const { t } = useTranslation();
  const { data: accounts } = useAsync(listAccounts, [], "accounting:accounts");
  const postable = (accounts ?? []).filter((a) => a.is_postable);
  const { data: customers } = useAsync(listCustomers, [], "sales:customers");
  const { data: suppliers } = useAsync(listSuppliers, [], "purchasing:suppliers");
  const [account, setAccount] = useState("");
  // Party filter encoded as "type:code" (e.g. "customer:CUST001"); "" = all parties.
  const [party, setParty] = useState("");
  const [partyType, partyCode] = party ? party.split(":") : ["", ""];

  const { data, loading, error, reload } = useAsync(
    () => (account ? generalLedger(account, { partyType, party: partyCode }) : Promise.resolve(null)),
    [account, party],
  );

  const exportQuery = partyCode
    ? `account=${account}&party_type=${partyType}&party=${encodeURIComponent(partyCode)}`
    : `account=${account}`;

  return (
    <section className="acct-page">
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
        <label className="acct-field">
          <span>{t("accounting.report.party")}</span>
          <select value={party} onChange={(e) => setParty(e.target.value)}>
            <option value="">{t("accounting.report.allParties")}</option>
            {(customers ?? []).length > 0 && (
              <optgroup label={t("accounting.report.customers")}>
                {(customers ?? []).map((c) => (
                  <option key={`c:${c.code}`} value={`customer:${c.code}`}>
                    {c.code} · {c.name}
                  </option>
                ))}
              </optgroup>
            )}
            {(suppliers ?? []).length > 0 && (
              <optgroup label={t("accounting.report.suppliers")}>
                {(suppliers ?? []).map((s) => (
                  <option key={`s:${s.code}`} value={`supplier:${s.code}`}>
                    {s.code} · {s.name}
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </label>
        {partyCode && (
          <PartyLink type={partyType as PartyType} code={partyCode} className="acct-link">
            {t("party.openParty")}
          </PartyLink>
        )}
        {data && (
          <span className="muted">
            {t("accounting.report.closing")}: <Bdi>{formatMinor(data.closing_balance)}</Bdi>
          </span>
        )}
      </div>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!account && <p className="muted">{t("accounting.report.pickAccount")}</p>}

      {data && account && <ExportButtons path={`/accounting/reports/general-ledger?${exportQuery}`} />}

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
                  <td className="latin">
                    <Link to={`/accounting/journals/${l.entry_id}`}>{l.entry_number}</Link>
                  </td>
                  <td>
                    {l.memo ? <Link to={`/accounting/journals/${l.entry_id}`}>{l.memo}</Link> : ""}
                  </td>
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
