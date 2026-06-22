import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createWarehouse, listWarehouses, type Warehouse } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

export function WarehousesPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listWarehouses, [], "inventory:warehouses");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<Warehouse>[]>(
    () => [
      { key: "code", label: t("inventory.warehouse.code"), type: "text", accessor: (w) => w.code },
      { key: "name", label: t("inventory.warehouse.name"), type: "text", accessor: (w) => w.name },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((w) => matchesAllFilters(w, fields, filters)) : data),
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
      await createWarehouse({ code, name });
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
    <section className="inv-page">
      <InventoryNav />

      <form className="card inv-toolbar" onSubmit={onSubmit}>
        <label className="inv-field">
          <span>{t("inventory.warehouse.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="inv-field">
          <span>{t("inventory.warehouse.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {t("inventory.warehouse.add")}
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
        <EmptyState title={t("inventory.warehouse.empty")} hint={t("inventory.warehouse.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="inv-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {filtered && filtered.length > 0 && (
        <div className="card inv-table-wrap">
          <table className="inv-table">
            <thead>
              <tr>
                <th>{t("inventory.warehouse.code")}</th>
                <th>{t("inventory.warehouse.name")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((w) => (
                <tr key={w.id}>
                  <td><Bdi>{w.code}</Bdi></td>
                  <td>{w.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
