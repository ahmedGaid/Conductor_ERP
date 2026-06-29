import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createWarehouse, listWarehouses, type Warehouse } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { EntityLink } from "../../components/EntityLink";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { InventoryNav } from "./InventoryNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./inventory.css";

export function WarehousesPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(listWarehouses, [], "inventory:warehouses");
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

  // Optimistic create: show the new warehouse row instantly and clear the form for the next entry;
  // the server row replaces the placeholder on settle, or it rolls back + toasts.
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const c = code.trim();
    const n = name.trim();
    if (!c || !n) return;
    void optimisticCreate<Warehouse>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, code: c, name: n }) as Warehouse,
      request: () => createWarehouse({ code: c, name: n }),
      toast,
      success: t("inventory.toast.warehouseCreated"),
    });
    setCode("");
    setName("");
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
        <button className="btn btn--primary" type="submit">
          {t("inventory.warehouse.add")}
        </button>
      </form>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

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
                  <td><EntityLink type="warehouse" value={w.code} /></td>
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
