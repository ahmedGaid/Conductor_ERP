import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { BackLink } from "../../components/BackLink";
import { useSetPageActions } from "../../app/PageActionsContext";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { copyShareLink, printDocument } from "../../lib/documentActions";

import {
  budgetVsActual,
  getBudget,
  listAccounts,
  listPeriods,
  setBudgetLine,
} from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { downloadExport } from "../../api/client";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./accounting.css";

export function BudgetDetailPage() {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const { id = "" } = useParams();
  const { data: budget, reload: reloadBudget } = useAsync(() => getBudget(id), [id], `accounting:budget:${id}`);
  const { data: accounts } = useAsync(listAccounts, [], "accounting:accounts");
  const { data: periods } = useAsync(listPeriods, [], "accounting:periods");
  const pnlAccounts = (accounts ?? []).filter(
    (a) => a.is_postable && a.is_active && (a.type === "income" || a.type === "expense"),
  );

  const [period, setPeriod] = useState("");
  const { data: variance, loading, error, reload: reloadVariance } =
    useAsync(() => budgetVsActual(id, period || undefined), [id, period]);

  useSetDocumentCrumb(budget?.name);

  // Line entry is a form (forms keep their controls) — no bar primary. The variance report's
  // CSV/Excel fold into this same ⋯ (unified-ui FILE_03 split pattern), reusing downloadExport.
  const barMenu = useMemo<DocMenuItem[]>(() => {
    if (!budget) return [];
    const menu: DocMenuItem[] = [
      { key: "print", label: t("document.print"), icon: "print", onClick: () => printDocument(budget.name) },
      { key: "pdf", label: t("document.exportPdf"), icon: "download", onClick: () => printDocument(budget.name) },
    ];
    if (variance) {
      const path = `/accounting/budgets/${id}/variance${period ? `?period=${period}` : ""}`;
      const sep = path.includes("?") ? "&" : "?";
      const download = (fmt: string) => () =>
        void downloadExport(`${path}${sep}export=${fmt}&lang=${i18n.language}`).catch((err) =>
          toast.show(err instanceof Error ? err.message : String(err), "error"),
        );
      menu.push(
        { key: "csv", label: t("export.csv"), icon: "download", onClick: download("csv") },
        { key: "excel", label: t("export.excel"), icon: "download", onClick: download("xlsx") },
      );
    }
    menu.push({
      key: "share",
      label: t("document.share"),
      icon: "share",
      onClick: () =>
        void copyShareLink(`/accounting/budgets/${id}`).then((ok) =>
          toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
        ),
    });
    return menu;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [budget, variance, period, i18n.language, t]);
  useSetPageActions({ menuItems: barMenu });

  // line entry
  const [account, setAccount] = useState("");
  const [linePeriod, setLinePeriod] = useState("");
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSetLine(e: FormEvent) {
    e.preventDefault();
    const amountMinor = parseToMinor(amount);
    if (!account || !linePeriod || amountMinor === null) {
      setFormError(t("accounting.budgets.invalidInput"));
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      await setBudgetLine(id, { account_code: account, period_code: linePeriod, amount_minor: amountMinor });
      setAmount("");
      reloadBudget();
      reloadVariance();
      toast.show(t("accounting.toast.budgetLineSet"), "success");
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="acct-page">
      <AccountingNav />
      <BackLink to="/accounting/budgets">{t("accounting.budgets.backToList")}</BackLink>

      {budget && (
        <div className="card acct-detail">
          <header className="acct-detail__head">
            <h2>{budget.name} · <Bdi>{budget.fiscal_year_code}</Bdi></h2>
          </header>

          <form className="acct-toolbar" onSubmit={onSetLine}>
            <label className="acct-field">
              <span>{t("accounting.budgets.account")}</span>
              <select className="latin" value={account} onChange={(e) => setAccount(e.target.value)} required>
                <option value="">—</option>
                {pnlAccounts.map((a) => (
                  <option key={a.code} value={a.code}>{a.code} · {a.name}</option>
                ))}
              </select>
            </label>
            <label className="acct-field">
              <span>{t("accounting.budgets.period")}</span>
              <select className="latin" value={linePeriod} onChange={(e) => setLinePeriod(e.target.value)} required>
                <option value="">—</option>
                {(periods ?? []).map((p) => (
                  <option key={p.code} value={p.code}>{p.code}</option>
                ))}
              </select>
            </label>
            <label className="acct-field">
              <span>{t("accounting.budgets.amount")}</span>
              <input className="latin" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} required />
            </label>
            <button className="btn" type="submit" disabled={busy}>{t("accounting.budgets.setLine")}</button>
          </form>
          <p className="hint">{t("accounting.budgets.setHint")}</p>
          {formError && <p className="error-text">{formError}</p>}
        </div>
      )}

      <div className="acct-toolbar">
        <label className="acct-field">
          <span>{t("accounting.budgets.period")}</span>
          <select className="latin" value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="">{t("accounting.budgets.wholeYear")}</option>
            {(periods ?? []).map((p) => (
              <option key={p.code} value={p.code}>{p.code}</option>
            ))}
          </select>
        </label>
      </div>

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reloadVariance} />}

      {variance && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.account.code")}</th>
                <th>{t("accounting.account.name")}</th>
                <th className="acct-table__num">{t("accounting.budgets.budget")}</th>
                <th className="acct-table__num">{t("accounting.budgets.actual")}</th>
                <th className="acct-table__num">{t("accounting.budgets.variance")}</th>
              </tr>
            </thead>
            <tbody>
              {variance.rows.map((r) => (
                <tr key={r.account_code}>
                  <td><Bdi>{r.account_code}</Bdi></td>
                  <td>{r.account_name}</td>
                  <td className="acct-table__num"><Bdi>{formatMinor(r.budget_minor)}</Bdi></td>
                  <td className="acct-table__num"><Bdi>{formatMinor(r.actual_minor)}</Bdi></td>
                  <td className={`acct-table__num ${r.variance_minor >= 0 ? "acct-balanced" : "acct-unbalanced"}`}>
                    <Bdi>{formatMinor(r.variance_minor)}</Bdi>
                  </td>
                </tr>
              ))}
              {variance.rows.length === 0 && (
                <tr><td colSpan={5} className="muted">{t("accounting.budgets.noLines")}</td></tr>
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={2}>{t("accounting.entry.totals")}</td>
                <td className="acct-table__num"><Bdi>{formatMinor(variance.total_budget)}</Bdi></td>
                <td className="acct-table__num"><Bdi>{formatMinor(variance.total_actual)}</Bdi></td>
                <td className="acct-table__num"><Bdi>{formatMinor(variance.total_variance)}</Bdi></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </section>
  );
}
