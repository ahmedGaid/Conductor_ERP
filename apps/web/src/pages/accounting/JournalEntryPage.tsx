import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { listAccounts, listCostCenters, postJournal, type JournalLineInput } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

interface DraftLine {
  account_code: string;
  debit: string;
  credit: string;
  memo: string;
  cost_center_code: string;
}

const emptyLine = (): DraftLine => ({ account_code: "", debit: "", credit: "", memo: "", cost_center_code: "" });

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function JournalEntryPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: accounts } = useAsync(listAccounts, [], "accounting:accounts");
  const { data: costCenters } = useAsync(listCostCenters, [], "accounting:cost-centers");
  const postable = (accounts ?? []).filter((a) => a.is_postable && a.is_active);
  const activeCostCenters = (costCenters ?? []).filter((c) => c.is_active);

  const [date, setDate] = useState(today());
  const [memo, setMemo] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([emptyLine(), emptyLine()]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function setLine(i: number, patch: Partial<DraftLine>) {
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  const totalDebit = lines.reduce((s, l) => s + (parseToMinor(l.debit) ?? 0), 0);
  const totalCredit = lines.reduce((s, l) => s + (parseToMinor(l.credit) ?? 0), 0);
  const balanced = totalDebit === totalCredit && totalDebit > 0;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const payloadLines: JournalLineInput[] = [];
    for (const l of lines) {
      const debit = parseToMinor(l.debit);
      const credit = parseToMinor(l.credit);
      if (debit === null || credit === null) {
        setError(t("accounting.entry.invalidAmount"));
        return;
      }
      if (!l.account_code || (debit === 0 && credit === 0)) continue;
      payloadLines.push({
        account_code: l.account_code,
        debit,
        credit,
        memo: l.memo,
        cost_center_code: l.cost_center_code,
      });
    }
    if (payloadLines.length < 2) {
      setError(t("accounting.entry.needLines"));
      return;
    }

    setBusy(true);
    try {
      const entry = await postJournal({ date, memo, lines: payloadLines });
      navigate(`/accounting/journals/${entry.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
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
            <span>{t("accounting.entry.date")}</span>
            <input type="date" className="latin" value={date} onChange={(e) => setDate(e.target.value)} required />
          </label>
          <label className="acct-field" style={{ flex: 1 }}>
            <span>{t("accounting.entry.memo")}</span>
            <input value={memo} onChange={(e) => setMemo(e.target.value)} />
          </label>
        </div>

        <div className="acct-table-wrap" style={{ marginBlock: "var(--space-4)" }}>
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.entry.account")}</th>
                <th className="acct-table__num">{t("accounting.entry.debit")}</th>
                <th className="acct-table__num">{t("accounting.entry.credit")}</th>
                <th>{t("accounting.entry.costCenter")}</th>
                <th>{t("accounting.entry.lineMemo")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {lines.map((l, i) => (
                <tr key={i}>
                  <td>
                    <select
                      value={l.account_code}
                      onChange={(e) => setLine(i, { account_code: e.target.value })}
                    >
                      <option value="">—</option>
                      {postable.map((a) => (
                        <option key={a.code} value={a.code}>
                          {a.code} · {a.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="acct-table__num">
                    <input
                      className="latin"
                      inputMode="decimal"
                      value={l.debit}
                      onChange={(e) => setLine(i, { debit: e.target.value, credit: "" })}
                    />
                  </td>
                  <td className="acct-table__num">
                    <input
                      className="latin"
                      inputMode="decimal"
                      value={l.credit}
                      onChange={(e) => setLine(i, { credit: e.target.value, debit: "" })}
                    />
                  </td>
                  <td>
                    <select
                      value={l.cost_center_code}
                      onChange={(e) => setLine(i, { cost_center_code: e.target.value })}
                    >
                      <option value="">—</option>
                      {activeCostCenters.map((c) => (
                        <option key={c.code} value={c.code}>
                          {c.code} · {c.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input value={l.memo} onChange={(e) => setLine(i, { memo: e.target.value })} />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn--sm"
                      onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))}
                      disabled={lines.length <= 2}
                      aria-label={t("common.delete")}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td>{t("accounting.entry.totals")}</td>
                <td className="acct-table__num"><Bdi>{formatMinor(totalDebit)}</Bdi></td>
                <td className="acct-table__num"><Bdi>{formatMinor(totalCredit)}</Bdi></td>
                <td colSpan={3}>
                  <span className={balanced ? "acct-balanced" : "acct-unbalanced"}>
                    {balanced ? t("accounting.entry.balanced") : t("accounting.entry.unbalanced")}
                  </span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        <div className="acct-toolbar">
          <button type="button" className="btn btn--sm" onClick={() => setLines((ls) => [...ls, emptyLine()])}>
            {t("accounting.entry.addLine")}
          </button>
          <button type="submit" className="btn btn--primary" disabled={busy || !balanced}>
            {t("accounting.entry.post")}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </form>
    </section>
  );
}
