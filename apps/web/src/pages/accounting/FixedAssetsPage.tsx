import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { acquireAsset, getAsset, listAssets, runDepreciation, type AssetStatus, type FixedAsset } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useToast } from "../../app/ToastContext";
import { prefetch } from "../../lib/prefetch";
import { formatMinor, parseToMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { ExportButtons } from "../../components/ExportButtons";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./accounting.css";

const ASSET_STATUSES: AssetStatus[] = ["active", "disposed"];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function currentPeriod(): string {
  return today().slice(0, 7); // YYYY-MM
}

export function FixedAssetsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(listAssets, [], "accounting:assets");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<FixedAsset>[]>(
    () => [
      { key: "code", label: t("accounting.assets.code"), type: "text", accessor: (a) => a.code },
      { key: "name", label: t("accounting.assets.name"), type: "text", accessor: (a) => a.name },
      {
        key: "status",
        label: t("accounting.assets.status"),
        type: "select",
        options: ASSET_STATUSES.map((s) => ({ value: s, label: t(`accounting.assets.statuses.${s}`) })),
        accessor: (a) => a.status,
      },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((a) => matchesAllFilters(a, fields, filters)) : data),
    [data, fields, filters],
  );

  const statusTabs = useMemo(
    () => ASSET_STATUSES.map((s) => ({ value: s, label: t(`accounting.assets.statuses.${s}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((a) => a.status === tab)) : filtered),
    [filtered, tab],
  );

  // j/k move a row highlight, Enter/o opens it on the detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<FixedAsset>({
    items: visible ?? [],
    onOpen: (a) => navigate(`/accounting/assets/${encodeURIComponent(a.code)}`),
    persistKey: "accounting:assets",
    getItemId: (a) => a.code,
  });

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

  // A depreciation run touches an unknown set of assets server-side, so it can't be predicted; run
  // it, report the count and total posted via toast, and refresh the register.
  async function onRunDepreciation(e: FormEvent) {
    e.preventDefault();
    setRunBusy(true);
    try {
      const res = await runDepreciation(runPeriod, runDate);
      reload();
      toast.show(t("accounting.assets.runDone", { count: res.count, total: formatMinor(res.total_minor) }), "success");
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
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
        </form>
      </div>
      {formError && <p className="error-text">{formError}</p>}

      {loading && (
        <ListSkeleton rows={3} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("accounting.assets.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <>
          <div className="acct-toolbar-row">
            <FilterBar fields={fields} filters={filters} onChange={setFilters} />
            <ExportButtons path="/accounting/reports/asset-register" />
          </div>
          {filtered && (
            <StatusTabs
              rows={filtered}
              tabs={statusTabs}
              accessor={(a) => a.status}
              value={tab}
              onChange={setTab}
              ariaLabel={t("accounting.assets.status")}
            />
          )}
          {visible && visible.length === 0 && (
            <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
          )}
          {visible && visible.length > 0 && (
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
                {visible.map((a, i) => (
                  <tr key={a.id} data-kbd-active={i === active ? "true" : undefined} aria-selected={i === active}>
                    <td>
                      <Link
                        className="acct-link"
                        to={`/accounting/assets/${encodeURIComponent(a.code)}`}
                        onMouseEnter={() => prefetch(`accounting:asset:${a.code}`, () => getAsset(a.code))}
                        onFocus={() => prefetch(`accounting:asset:${a.code}`, () => getAsset(a.code))}
                      >
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
          )}
        </>
      )}
    </section>
  );
}
