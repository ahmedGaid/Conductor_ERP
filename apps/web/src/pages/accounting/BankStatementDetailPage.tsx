import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { NavIcon } from "../../app/icons";
import { BackLink } from "../../components/BackLink";
import { Badge } from "../../components/Badge";

import {
  autoMatchStatement,
  getBankStatement,
  listAccounts,
  listMatchCandidates,
  matchBankLine,
  postBankAdjustment,
  reconcileStatement,
  unmatchBankLine,
  type BankStatement,
} from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./accounting.css";

export function BankStatementDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { id = "" } = useParams();
  const { data: stmt, loading, error, reload, mutate } = useAsync<BankStatement>(
    () => getBankStatement(id),
    [id],
    `accounting:bank-statement:${id}`,
  );
  const { data: candidates, reload: reloadCandidates } = useAsync(() => listMatchCandidates(id), [id]);
  const { data: accounts } = useAsync(listAccounts, [], "accounting:accounts");
  const contraAccounts = (accounts ?? []).filter((a) => a.is_postable && a.is_active && !a.is_cash);

  const [adjAmount, setAdjAmount] = useState("");
  const [adjContra, setAdjContra] = useState("");
  const [adjMemo, setAdjMemo] = useState("");
  const [adjError, setAdjError] = useState<string | null>(null);

  // Every bank-rec action returns the updated statement: reflect the change instantly, settle with
  // the server's version (it recomputes the reconciliation summary), refresh the GL match candidates,
  // and roll back + toast on failure. `optimistic` is identity for sweeps we can't predict.
  async function apply(
    request: () => Promise<BankStatement>,
    opts: { optimistic?: (s: BankStatement) => BankStatement; success?: string } = {},
  ) {
    if (!stmt) return;
    await runOptimistic<BankStatement, BankStatement>({
      current: stmt,
      mutate,
      optimistic: opts.optimistic ?? ((s) => s),
      request,
      settle: (_predicted, updated) => updated,
      toast,
      success: opts.success,
    });
    reloadCandidates();
  }

  async function onAdjust(e: FormEvent) {
    e.preventDefault();
    const amt = parseToMinor(adjAmount);
    if (amt === null || amt === 0 || !adjContra) {
      setAdjError(t("accounting.bankRec.invalidInput"));
      return;
    }
    setAdjError(null);
    await apply(
      () => postBankAdjustment(id, { amount_minor: amt, contra_account_code: adjContra, memo: adjMemo }),
      { success: t("accounting.toast.adjustmentPosted") },
    );
    setAdjAmount("");
    setAdjMemo("");
  }

  const rec = stmt?.reconciliation;

  return (
    <section className="acct-page">
      <AccountingNav />
      <BackLink to="/accounting/bank-reconciliation">{t("accounting.bankRec.backToList")}</BackLink>

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {stmt && (
        <>
          <div className="card acct-detail">
            <header className="acct-detail__head">
              <h2><Bdi>{stmt.account_code}</Bdi> · <Bdi>{stmt.statement_date}</Bdi></h2>
              <Badge tone={stmt.status === "reconciled" ? "completed" : "running"}>
                {t(`accounting.bankRec.statuses.${stmt.status}`)}
              </Badge>
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
                <button
                  className="btn"
                  onClick={() => apply(() => autoMatchStatement(id), { success: t("accounting.toast.autoMatched") })}
                >
                  {t("accounting.bankRec.autoMatch")}
                </button>
                <button
                  className="btn btn--primary"
                  disabled={!rec?.is_reconciled}
                  onClick={() =>
                    apply(() => reconcileStatement(id), {
                      optimistic: (s) => ({ ...s, status: "reconciled" }),
                      success: t("accounting.toast.reconciled"),
                    })
                  }
                >
                  {t("accounting.bankRec.markReconciled")}
                </button>
              </div>
            )}
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
                            <NavIcon name="check" /> {t("accounting.bankRec.matched")}
                            {stmt.status === "open" && (
                              <button
                                className="btn btn--sm"
                                onClick={() =>
                                  apply(() => unmatchBankLine(l.id), {
                                    optimistic: (s) => ({
                                      ...s,
                                      lines: s.lines.map((x) =>
                                        x.id === l.id ? { ...x, is_matched: false, matched_line_id: null } : x,
                                      ),
                                    }),
                                  })
                                }
                              >
                                {t("accounting.bankRec.unmatch")}
                              </button>
                            )}
                          </span>
                        ) : stmt.status === "open" ? (
                          <select
                            className="latin"
                            value=""
                            onChange={(e) =>
                              e.target.value &&
                              apply(() => matchBankLine(l.id, Number(e.target.value)), {
                                optimistic: (s) => ({
                                  ...s,
                                  lines: s.lines.map((x) => (x.id === l.id ? { ...x, is_matched: true } : x)),
                                }),
                              })
                            }
                          >
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
              <label className="acct-field grow">
                <span>{t("accounting.bankRec.memo")}</span>
                <input value={adjMemo} onChange={(e) => setAdjMemo(e.target.value)} />
              </label>
              <button className="btn" type="submit">{t("accounting.bankRec.postAdjustment")}</button>
              {adjError && <p className="error-text">{adjError}</p>}
            </form>
          )}
        </>
      )}
    </section>
  );
}
