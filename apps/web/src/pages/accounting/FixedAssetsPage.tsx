import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { acquireAsset, listAssets, runDepreciation } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ExportButtons } from "../../components/ExportButtons";
import { EmptyState } from "../../components/EmptyState";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function currentPeriod(): string {
  return today().slice(0, 7); // YYYY-MM
}

export function FixedAssetsPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listAssets, [], "accounting:assets");

  // New-asset form
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [cost, setCost] = useState("");
  const [salvage, setSalvage] = useState("0");
  const [life, setLife] = useState("60");
  const [acqDate, setAcqDate] = useState(today());
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Depreciation run
  const [runPeriod, setRunPeriod] = useState(currentPeriod());
  const [runDate, setRunDate] = useState(today());
  const [runMsg, setRunMsg] = useState<string | null>(null);
  const [runBusy, setRunBusy] = useState(false);

  async function onAcquire(e: FormEvent) {
    e.preventDefault();
    const costMinor = parseToMinor(cost);
    const salvageMinor = parseToMinor(salvage) ?? 0;
    const months = parseInt(life, 10);
    if (costMinor === null || costMinor <= 0 || !months) {
      setFormError(t("accounting.assets.invalidInput"));
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      await acquireAsset({
        code,
        name,
        acquisition_date: acqDate,
        cost_minor: costMinor,
        salvage_minor: salvageMinor,
        useful_life_months: months,
      });
      setCode("");
      setName("");
      setCost("");
      setSalvage("0");
      reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onRunDepreciation(e: FormEvent) {
    e.preventDefault();
    setRunBusy(true);
    setRunMsg(null);
    try {
      const res = await runDepreciation(runPeriod, runDate);
      setRunMsg(t("accounting.assets.runDone", { count: res.count, total: formatMinor(res.total_minor) }));
      reload();
    } catch (err) {
      setRunMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setRunBusy(false);
    }
  }

  return (
    <section className="acct-page">
      <AccountingNav />

      <div className="acct-asset-actions">
        <form className="card acct-toolbar" onSubmit={onAcquire}>
          <label className="acct-field">
            <span>{t("accounting.assets.code")}</span>
            <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
          </label>
          <label className="acct-field">
            <span>{t("accounting.assets.name")}</span>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label className="acct-field">
            <span>{t("accounting.assets.cost")}</span>
            <input className="latin" inputMode="decimal" value={cost} onChange={(e) => setCost(e.target.value)} required />
          </label>
          <label className="acct-field">
            <span>{t("accounting.assets.salvage")}</span>
            <input className="latin" inputMode="decimal" value={salvage} onChange={(e) => setSalvage(e.target.value)} />
          </label>
          <label className="acct-field">
            <span>{t("accounting.assets.life")}</span>
            <input className="latin" inputMode="numeric" value={life} onChange={(e) => setLife(e.target.value)} required />
          </label>
          <label className="acct-field">
            <span>{t("accounting.assets.acquired")}</span>
            <input className="latin" type="date" value={acqDate} onChange={(e) => setAcqDate(e.target.value)} required />
          </label>
          <button className="btn btn--primary" type="submit" disabled={busy}>
            {t("accounting.assets.add")}
          </button>
        </form>

        <form className="card acct-toolbar" onSubmit={onRunDepreciation}>
          <label className="acct-field">
            <span>{t("accounting.assets.runPeriod")}</span>
            <input className="latin" value={runPeriod} onChange={(e) => setRunPeriod(e.target.value)} required />
          </label>
          <label className="acct-field">
            <span>{t("accounting.assets.runDate")}</span>
            <input className="latin" type="date" value={runDate} onChange={(e) => setRunDate(e.target.value)} required />
          </label>
          <button className="btn" type="submit" disabled={runBusy}>
            {t("accounting.assets.runDepreciation")}
          </button>
          {runMsg && <span className="acct-asset-runmsg">{runMsg}</span>}
        </form>
      </div>
      {formError && <p className="error-text">{formError}</p>}

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}

      {data && data.length === 0 && (
        <EmptyState title={t("accounting.assets.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <>
          <ExportButtons path="/accounting/reports/asset-register" />
          <div className="card acct-table-wrap">
            <table className="acct-table">
              <thead>
                <tr>
                  <th>{t("accounting.assets.code")}</th>
                  <th>{t("accounting.assets.name")}</th>
                  <th className="acct-table__num">{t("accounting.assets.cost")}</th>
                  <th className="acct-table__num">{t("accounting.assets.accumulated")}</th>
                  <th className="acct-table__num">{t("accounting.assets.nbv")}</th>
                  <th>{t("accounting.assets.status")}</th>
                </tr>
              </thead>
              <tbody>
                {data.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <Link className="acct-link" to={`/accounting/assets/${encodeURIComponent(a.code)}`}>
                        <Bdi>{a.code}</Bdi>
                      </Link>
                    </td>
                    <td>{a.name}</td>
                    <td className="acct-table__num"><Bdi>{formatMinor(a.cost_minor)}</Bdi></td>
                    <td className="acct-table__num"><Bdi>{formatMinor(a.accumulated_depreciation_minor)}</Bdi></td>
                    <td className="acct-table__num"><Bdi>{formatMinor(a.net_book_value_minor)}</Bdi></td>
                    <td>
                      <span className={`pill pill--${a.status === "active" ? "running" : "completed"}`}>
                        {t(`accounting.assets.statuses.${a.status}`)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
