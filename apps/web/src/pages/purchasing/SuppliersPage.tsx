import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createSupplier, listSuppliers, type Supplier } from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

export function SuppliersPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listSuppliers, [], "purchasing:suppliers");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<Supplier>[]>(
    () => [
      { key: "code", label: t("purchasing.supplier.code"), type: "text", accessor: (s) => s.code },
      { key: "name", label: t("purchasing.supplier.name"), type: "text", accessor: (s) => s.name },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((s) => matchesAllFilters(s, fields, filters)) : data),
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
      await createSupplier({ code, name });
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
    <section className="pur-page">
      <PurchasingNav />

      <form className="card pur-toolbar" onSubmit={onSubmit}>
        <label className="pur-field">
          <span>{t("purchasing.supplier.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="pur-field">
          <span>{t("purchasing.supplier.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {t("purchasing.supplier.add")}
        </button>
      </form>
      {formError && <p className="error-text">{formError}</p>}

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}

      {data && data.length === 0 && (
        <EmptyState title={t("purchasing.supplier.empty")} hint={t("purchasing.supplier.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="pur-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {filtered && filtered.length > 0 && (
        <div className="card pur-table-wrap">
          <table className="pur-table">
            <thead>
              <tr>
                <th>{t("purchasing.supplier.code")}</th>
                <th>{t("purchasing.supplier.name")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id}>
                  <td><Bdi>{s.code}</Bdi></td>
                  <td>{s.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
