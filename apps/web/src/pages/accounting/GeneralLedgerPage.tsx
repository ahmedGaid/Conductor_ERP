import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { generalLedger, listAccounts } from "../../api/accounting";
import { listCustomers } from "../../api/sales";
import { listSuppliers } from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { formatMoneyNumeral, formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { PartyLink, type PartyType } from "../../components/PartyLink";
import { useReportPageActions } from "../../hooks/useReportPageActions";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import { ComboBox } from "../../components/ComboBox";
import "./accounting.css";
import { codeAndName } from "../../lib/bilingualName";

export function GeneralLedgerPage() {
  const { t, i18n } = useTranslation();
  const { data: accounts } = useAsync(listAccounts, [], "accounting:accounts");
  const postable = (accounts ?? []).filter((a) => a.is_postable);
  const { data: customers } = useAsync(listCustomers, [], "sales:customers");
  const { data: suppliers } = useAsync(listSuppliers, [], "purchasing:suppliers");
  const [account, setAccount] = useState("");
  // Party filter encoded as "type:code" (e.g. "customer:CUST001"); "" = all parties.
  const [party, setParty] = useState("");
  const [partyType, partyCode] = party ? party.split(":") : ["", ""];

  const accountOptions = postable.map((a) => ({ value: a.code, label: codeAndName(a, i18n.language) }));
  const partyOptions = [
    { value: "", label: t("accounting.report.allParties") },
    ...(customers ?? []).map((c) => ({
      value: `customer:${c.code}`,
      label: `${t("accounting.report.customers")} · ${c.code} · ${c.name}`,
    })),
    ...(suppliers ?? []).map((s) => ({
      value: `supplier:${s.code}`,
      label: `${t("accounting.report.suppliers")} · ${s.code} · ${s.name}`,
    })),
  ];

  const { data, loading, error, reload } = useAsync(
    () => (account ? generalLedger(account, { partyType, party: partyCode }) : Promise.resolve(null)),
    [account, party],
  );

  const exportQuery = partyCode
    ? `account=${account}&party_type=${partyType}&party=${encodeURIComponent(partyCode)}`
    : `account=${account}`;

  useReportPageActions(data && account ? `/accounting/reports/general-ledger?${exportQuery}` : null);

  return (
    <section className="acct-page">
      <AccountingNav />

      <div className="acct-toolbar">
        <label className="acct-field">
          <span>{t("accounting.entry.account")}</span>
          <ComboBox
            options={accountOptions}
            value={account}
            onChange={setAccount}
            placeholder={t("accounting.report.pickAccount")}
          />
        </label>
        <label className="acct-field">
          <span>{t("accounting.report.party")}</span>
          <ComboBox
            options={partyOptions}
            value={party}
            onChange={setParty}
            placeholder={t("accounting.report.allParties")}
          />
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

      {data && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.entry.date")}</th>
                <th>{t("accounting.journals.number")}</th>
                <th>{t("accounting.entry.memo")}</th>
                <th className="acct-table__num">{t("accounting.entry.debit")} (EGP)</th>
                <th className="acct-table__num">{t("accounting.entry.credit")} (EGP)</th>
                <th className="acct-table__num">{t("accounting.report.running")} (EGP)</th>
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
                  <td className="acct-table__num"><Bdi>{l.debit ? formatMoneyNumeral(l.debit) : ""}</Bdi></td>
                  <td className="acct-table__num"><Bdi>{l.credit ? formatMoneyNumeral(l.credit) : ""}</Bdi></td>
                  <td className="acct-table__num"><Bdi>{formatMoneyNumeral(l.running_balance)}</Bdi></td>
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
