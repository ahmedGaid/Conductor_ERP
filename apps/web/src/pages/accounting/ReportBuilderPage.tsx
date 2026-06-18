import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  createReportDefinition,
  deleteReportDefinition,
  listReportDefinitions,
  runReportDefinition,
  type AccountType,
  type ReportGroupBy,
  type ReportSchedule,
} from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ExportButtons } from "../../components/ExportButtons";
import { EmptyState } from "../../components/EmptyState";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

const TYPES: AccountType[] = ["asset", "liability", "equity", "income", "expense"];
const GROUPS: ReportGroupBy[] = ["account", "period"];
const SCHEDULES: ReportSchedule[] = ["none", "daily", "weekly", "monthly"];

export function ReportBuilderPage() {
  const { t } = useTranslation();
  const { data: defs, loading, error, reload } = useAsync(listReportDefinitions, [], "accounting:report-definitions");

  const [name, setName] = useState("");
  const [accountType, setAccountType] = useState("");
  const [codes, setCodes] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [groupBy, setGroupBy] = useState<ReportGroupBy>("account");
  const [schedule, setSchedule] = useState<ReportSchedule>("none");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [runId, setRunId] = useState<string | null>(null);
  const { data: result } = useAsync(
    () => (runId ? runReportDefinition(runId) : Promise.resolve(null)),
    [runId],
  );

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!name) {
      setFormError(t("accounting.reportBuilder.needName"));
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      await createReportDefinition({
        name,
        account_type: accountType,
        account_codes: codes,
        date_from: from || null,
        date_to: to || null,
        group_by: groupBy,
        schedule,
      });
      setName("");
      setCodes("");
      reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: string) {
    setBusy(true);
    try {
      await deleteReportDefinition(id);
      if (runId === id) setRunId(null);
      reload();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="acct-page">
      <h1>{t("nav.accounting")}</h1>
      <AccountingNav />

      <form className="card acct-toolbar" onSubmit={onCreate}>
        <label className="acct-field">
          <span>{t("accounting.reportBuilder.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="acct-field">
          <span>{t("accounting.reportBuilder.accountType")}</span>
          <select value={accountType} onChange={(e) => setAccountType(e.target.value)}>
            <option value="">{t("accounting.reportBuilder.allTypes")}</option>
            {TYPES.map((ty) => (
              <option key={ty} value={ty}>{t(`accounting.types.${ty}`)}</option>
            ))}
          </select>
        </label>
        <label className="acct-field">
          <span>{t("accounting.reportBuilder.codes")}</span>
          <input className="latin" value={codes} onChange={(e) => setCodes(e.target.value)} placeholder="1000,4000" />
        </label>
        <label className="acct-field">
          <span>{t("accounting.report.from")}</span>
          <input className="latin" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label className="acct-field">
          <span>{t("accounting.report.to")}</span>
          <input className="latin" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
        <label className="acct-field">
          <span>{t("accounting.reportBuilder.groupBy")}</span>
          <select value={groupBy} onChange={(e) => setGroupBy(e.target.value as ReportGroupBy)}>
            {GROUPS.map((g) => (
              <option key={g} value={g}>{t(`accounting.reportBuilder.groups.${g}`)}</option>
            ))}
          </select>
        </label>
        <label className="acct-field">
          <span>{t("accounting.reportBuilder.schedule")}</span>
          <select value={schedule} onChange={(e) => setSchedule(e.target.value as ReportSchedule)}>
            {SCHEDULES.map((s) => (
              <option key={s} value={s}>{t(`accounting.reportBuilder.schedules.${s}`)}</option>
            ))}
          </select>
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>{t("accounting.reportBuilder.save")}</button>
      </form>
      <p className="muted" style={{ fontSize: "var(--font-size-sm)" }}>{t("accounting.reportBuilder.scheduleHint")}</p>
      {formError && <p className="error-text">{formError}</p>}

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}

      {defs && defs.length === 0 && (
        <EmptyState title={t("accounting.reportBuilder.empty")} hint={t("common.emptyHint")} />
      )}

      {defs && defs.length > 0 && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.reportBuilder.name")}</th>
                <th>{t("accounting.reportBuilder.groupBy")}</th>
                <th>{t("accounting.reportBuilder.schedule")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {defs.map((d) => (
                <tr key={d.id}>
                  <td>{d.name}</td>
                  <td>{t(`accounting.reportBuilder.groups.${d.group_by}`)}</td>
                  <td>{t(`accounting.reportBuilder.schedules.${d.schedule}`)}</td>
                  <td>
                    <div className="acct-toolbar">
                      <button className="btn btn--sm btn--primary" disabled={busy} onClick={() => setRunId(d.id)}>
                        {t("accounting.reportBuilder.run")}
                      </button>
                      <button className="btn btn--sm btn--danger" disabled={busy} onClick={() => onDelete(d.id)}>
                        {t("common.delete")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {result && runId && (
        <>
          <h2 className="acct-detail__action-title">{result.name}</h2>
          <ExportButtons path={`/accounting/report-definitions/${runId}/run`} />
          <div className="card acct-table-wrap">
            <table className="acct-table">
              <thead>
                <tr>
                  <th>{result.group_by === "account" ? t("accounting.account.name") : t("accounting.report.period")}</th>
                  <th className="acct-table__num">{t("accounting.entry.debit")}</th>
                  <th className="acct-table__num">{t("accounting.entry.credit")}</th>
                  <th className="acct-table__num">{t("accounting.reportBuilder.balance")}</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((r) => (
                  <tr key={r.group_key}>
                    <td><Bdi>{r.group_label}</Bdi></td>
                    <td className="acct-table__num"><Bdi>{formatMinor(r.debit)}</Bdi></td>
                    <td className="acct-table__num"><Bdi>{formatMinor(r.credit)}</Bdi></td>
                    <td className="acct-table__num"><Bdi>{formatMinor(r.balance)}</Bdi></td>
                  </tr>
                ))}
                {result.rows.length === 0 && (
                  <tr><td colSpan={4} className="muted">{t("accounting.report.noActivity")}</td></tr>
                )}
              </tbody>
              <tfoot>
                <tr>
                  <td>{t("accounting.entry.totals")}</td>
                  <td className="acct-table__num"><Bdi>{formatMinor(result.total_debit)}</Bdi></td>
                  <td className="acct-table__num"><Bdi>{formatMinor(result.total_credit)}</Bdi></td>
                  <td className="acct-table__num"><Bdi>{formatMinor(result.total_balance)}</Bdi></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
