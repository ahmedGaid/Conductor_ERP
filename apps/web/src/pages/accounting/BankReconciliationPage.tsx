import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { createBankStatement, listAccounts, listBankStatements } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

interface DraftLine {
  date: string;
  amount: string;
  description: string;
}

const emptyLine = (d: string): DraftLine => ({ date: d, amount: "", description: "" });

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function BankReconciliationPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(listBankStatements, [], "accounting:bank-statements");
  const { data: accounts } = useAsync(listAccounts, [], "accounting:accounts");
  const cashAccounts = (accounts ?? []).filter((a) => a.is_cash && a.is_active);

  const [account, setAccount] = useState("");
  const [stmtDate, setStmtDate] = useState(today());
  const [closing, setClosing] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([emptyLine(today())]);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function setLine(i: number, patch: Partial<DraftLine>) {
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const closingMinor = parseToMinor(closing);
    if (!account || closingMinor === null) {
      setFormError(t("accounting.bankRec.invalidInput"));
      return;
    }
    const payloadLines = [];
    for (const l of lines) {
      const amt = parseToMinor(l.amount);
      if (amt === null) {
        setFormError(t("accounting.bankRec.invalidInput"));
        return;
      }
      if (amt === 0) continue;
      payloadLines.push({ date: l.date, amount_minor: amt, description: l.description });
    }
    setBusy(true);
    setFormError(null);
    try {
      const stmt = await createBankStatement({
        account_code: account,
        statement_date: stmtDate,
        closing_balance_minor: closingMinor,
        lines: payloadLines,
      });
      reload();
      navigate(`/accounting/bank-reconciliation/${stmt.id}`);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="acct-page">
      <AccountingNav />

      <form className="card" onSubmit={onSubmit}>
        <div className="acct-toolbar">
          <label className="acct-field">
            <span>{t("accounting.bankRec.account")}</span>
            <select className="latin" value={account} onChange={(e) => setAccount(e.target.value)} required>
              <option value="">—</option>
              {cashAccounts.map((a) => (
                <option key={a.code} value={a.code}>{a.code} · {a.name}</option>
              ))}
            </select>
          </label>
          <label className="acct-field">
            <span>{t("accounting.bankRec.statementDate")}</span>
            <input className="latin" type="date" value={stmtDate} onChange={(e) => setStmtDate(e.target.value)} required />
          </label>
          <label className="acct-field">
            <span>{t("accounting.bankRec.closingBalance")}</span>
            <input className="latin" inputMode="decimal" value={closing} onChange={(e) => setClosing(e.target.value)} required />
          </label>
        </div>

        <div className="acct-table-wrap" style={{ marginBlock: "var(--space-4)" }}>
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.bankRec.lineDate")}</th>
                <th className="acct-table__num">{t("accounting.bankRec.amount")}</th>
                <th>{t("accounting.bankRec.description")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {lines.map((l, i) => (
                <tr key={i}>
                  <td>
                    <input className="latin" type="date" value={l.date} onChange={(e) => setLine(i, { date: e.target.value })} />
                  </td>
                  <td className="acct-table__num">
                    <input className="latin" inputMode="decimal" value={l.amount}
                           placeholder="±0.00" onChange={(e) => setLine(i, { amount: e.target.value })} />
                  </td>
                  <td>
                    <input value={l.description} onChange={(e) => setLine(i, { description: e.target.value })} />
                  </td>
                  <td>
                    <button type="button" className="btn btn--sm"
                            onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))}
                            disabled={lines.length <= 1} aria-label={t("common.delete")}>✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="acct-toolbar">
          <button type="button" className="btn btn--sm" onClick={() => setLines((ls) => [...ls, emptyLine(today())])}>
            {t("accounting.bankRec.addLine")}
          </button>
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {t("accounting.bankRec.create")}
          </button>
        </div>
        <p className="muted" style={{ fontSize: "var(--font-size-sm)" }}>{t("accounting.bankRec.amountHint")}</p>
        {formError && <p className="error-text">{formError}</p>}
      </form>

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}

      {data && data.length === 0 && (
        <EmptyState title={t("accounting.bankRec.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.bankRec.account")}</th>
                <th>{t("accounting.bankRec.statementDate")}</th>
                <th className="acct-table__num">{t("accounting.bankRec.closingBalance")}</th>
                <th>{t("accounting.costCenters.active")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.id}>
                  <td>
                    <Link className="acct-link" to={`/accounting/bank-reconciliation/${s.id}`}>
                      <Bdi>{s.account_code}</Bdi>
                    </Link>
                  </td>
                  <td><Bdi>{s.statement_date}</Bdi></td>
                  <td className="acct-table__num"><Bdi>{formatMinor(s.closing_balance_minor)}</Bdi></td>
                  <td>
                    <span className={`pill pill--${s.status === "reconciled" ? "completed" : "running"}`}>
                      {t(`accounting.bankRec.statuses.${s.status}`)}
                    </span>
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
