import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createCostCenter, listCostCenters } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

type CostCenter = Awaited<ReturnType<typeof listCostCenters>>[number];

export function CostCentersPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listCostCenters, [], "accounting:cost-centers");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<CostCenter>[]>(
    () => [
      { key: "code", label: t("accounting.costCenters.code"), type: "text", accessor: (cc) => cc.code },
      { key: "name", label: t("accounting.costCenters.name"), type: "text", accessor: (cc) => cc.name },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((cc) => matchesAllFilters(cc, fields, filters)) : data),
    [data, fields, filters],
  );

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      await createCostCenter({ code, name });
      setCode("");
      setName("");
      reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="acct-page">
      <AccountingNav />

      <form className="card acct-toolbar" onSubmit={onSubmit}>
        <label className="acct-field">
          <span>{t("accounting.costCenters.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="acct-field" style={{ flex: 1 }}>
          <span>{t("accounting.costCenters.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {t("accounting.costCenters.add")}
        </button>
      </form>
      {formError && <p className="error-text">{formError}</p>}

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
        <EmptyState title={t("accounting.costCenters.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="acct-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {filtered && filtered.length > 0 && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.costCenters.code")}</th>
                <th>{t("accounting.costCenters.name")}</th>
                <th>{t("accounting.costCenters.active")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((cc) => (
                <tr key={cc.id}>
                  <td><Bdi>{cc.code}</Bdi></td>
                  <td>{cc.name}</td>
                  <td>{cc.is_active ? t("common.yes") : t("common.no")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
