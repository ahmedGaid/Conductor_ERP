import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import {
  autoMatchStatement,
  getBankStatement,
  listAccounts,
  listMatchCandidates,
  matchBankLine,
  postBankAdjustment,
  reconcileStatement,
  unmatchBankLine,
} from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

export function BankStatementDetailPage() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const { data: stmt, loading, error, reload } = useAsync(() => getBankStatement(id), [id]);
  const { data: candidates, reload: reloadCandidates } = useAsync(() => listMatchCandidates(id), [id]);
  const { data: accounts } = useAsync(listAccounts, [], "accounting:accounts");
  const contraAccounts = (accounts ?? []).filter((a) => a.is_postable && a.is_active && !a.is_cash);

  const [adjAmount, setAdjAmount] = useState("");
  const [adjContra, setAdjContra] = useState("");
  const [adjMemo, setAdjMemo] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setActionError(null);
    try {
      await fn();
      reload();
      reloadCandidates();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onAdjust(e: FormEvent) {
    e.preventDefault();
    const amt = parseToMinor(adjAmount);
    if (amt === null || amt === 0 || !adjContra) {
      setActionError(t("accounting.bankRec.invalidInput"));
      return;
    }
    await run(() => postBankAdjustment(id, { amount_minor: amt, contra_account_code: adjContra, memo: adjMemo }));
    setAdjAmount("");
    setAdjMemo("");
  }

  const rec = stmt?.reconciliation;

  return (
    <section className="acct-page">
      <h1>{t("nav.accounting")}</h1>
      <AccountingNav />
      <Link className="acct-link" to="/accounting/bank-reconciliation">← {t("accounting.bankRec.backToList")}</Link>

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}

      {stmt && (
        <>
          <div className="card acct-detail">
            <header className="acct-detail__head">
              <h2><Bdi>{stmt.account_code}</Bdi> · <Bdi>{stmt.statement_date}</Bdi></h2>
              <span className={`pill pill--${stmt.status === "reconciled" ? "completed" : "running"}`}>
                {t(`accounting.bankRec.statuses.${stmt.status}`)}
              </span>
            </header>
            {rec && (
              <dl className="acct-detail__grid">
                <div><dt>{t("accounting.bankRec.statementClosing")}</dt><dd><Bdi>{formatMinor(rec.statement_closing)}</Bdi></dd></div>
                <div><dt>{t("accounting.bankRec.bookBalance")}</dt><dd><Bdi>{formatMinor(rec.book_balance)}</Bdi></dd></div>
                <div>
                  <dt>{t("accounting.bankRec.difference")}</dt>
                  <dd className={rec.difference === 0 ? "acct-balanced" : "acct-unbalanced"}><Bdi>{formatMinor(rec.difference)}</Bdi></dd>
                </div>
                <div>
                  <dt>{t("accounting.bankRec.reconciled")}</dt>
                  <dd className={rec.is_reconciled ? "acct-balanced" : "acct-unbalanced"}>
                    {rec.is_reconciled ? t("common.yes") : t("common.no")}
                  </dd>
                </div>
              </dl>
            )}
            {stmt.status === "open" && (
              <div className="acct-toolbar">
                <button className="btn" disabled={busy} onClick={() => run(() => autoMatchStatement(id))}>
                  {t("accounting.bankRec.autoMatch")}
                </button>
                <button className="btn btn--primary" disabled={busy || !rec?.is_reconciled}
                        onClick={() => run(() => reconcileStatement(id))}>
                  {t("accounting.bankRec.markReconciled")}
                </button>
              </div>
            )}
            {actionError && <p className="error-text">{actionError}</p>}
          </div>

          <div className="card acct-table-wrap">
            <table className="acct-table">
              <thead>
                <tr>
                  <th>{t("accounting.bankRec.lineDate")}</th>
                  <th>{t("accounting.bankRec.description")}</th>
                  <th className="acct-table__num">{t("accounting.bankRec.amount")}</th>
                  <th>{t("accounting.bankRec.match")}</th>
                </tr>
              </thead>
              <tbody>
                {stmt.lines.map((l) => {
                  const lineCandidates = (candidates ?? []).filter((c) => c.amount_minor === l.amount_minor);
                  return (
                    <tr key={l.id}>
                      <td><Bdi>{l.date}</Bdi></td>
                      <td>{l.description}</td>
                      <td className="acct-table__num"><Bdi>{formatMinor(l.amount_minor)}</Bdi></td>
                      <td>
                        {l.is_matched ? (
                          <span className="acct-bankrec-matched">
                            ✓ {t("accounting.bankRec.matched")}
                            {stmt.status === "open" && (
                              <button className="btn btn--sm" disabled={busy}
                                      onClick={() => run(() => unmatchBankLine(l.id))}>
                                {t("accounting.bankRec.unmatch")}
                              </button>
                            )}
                          </span>
                        ) : stmt.status === "open" ? (
                          <select className="latin" disabled={busy} value=""
                                  onChange={(e) => e.target.value && run(() => matchBankLine(l.id, Number(e.target.value)))}>
                            <option value="">{lineCandidates.length ? t("accounting.bankRec.pickLedgerLine") : t("accounting.bankRec.noCandidate")}</option>
                            {lineCandidates.map((c) => (
                              <option key={c.id} value={c.id}>{c.entry_number} · {c.date} · {formatMinor(c.amount_minor)}</option>
                            ))}
                          </select>
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {stmt.lines.length === 0 && (
                  <tr><td colSpan={4} className="muted">{t("accounting.bankRec.noLines")}</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {stmt.status === "open" && (
            <form className="card acct-toolbar" onSubmit={onAdjust}>
              <h3 className="acct-detail__action-title">{t("accounting.bankRec.adjustment")}</h3>
              <label className="acct-field">
                <span>{t("accounting.bankRec.amount")}</span>
                <input className="latin" inputMode="decimal" value={adjAmount} placeholder="±0.00"
                       onChange={(e) => setAdjAmount(e.target.value)} required />
              </label>
              <label className="acct-field">
                <span>{t("accounting.bankRec.contraAccount")}</span>
                <select className="latin" value={adjContra} onChange={(e) => setAdjContra(e.target.value)} required>
                  <option value="">—</option>
                  {contraAccounts.map((a) => (
                    <option key={a.code} value={a.code}>{a.code} · {a.name}</option>
                  ))}
                </select>
              </label>
              <label className="acct-field" style={{ flex: 1 }}>
                <span>{t("accounting.bankRec.memo")}</span>
                <input value={adjMemo} onChange={(e) => setAdjMemo(e.target.value)} />
              </label>
              <button className="btn" type="submit" disabled={busy}>{t("accounting.bankRec.postAdjustment")}</button>
            </form>
          )}
        </>
      )}
    </section>
  );
}
