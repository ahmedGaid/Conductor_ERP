import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createWarehouse, listWarehouses, type Warehouse } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { useFormKeys } from "../../hooks/useFormKeys";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { EntityLink } from "../../components/EntityLink";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
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
  const savedViews = useSavedViews({ listKey: "inventory:warehouses", fields, filters, setFilters });
  const filtered = useMemo(
    () => (data ? data.filter((w) => matchesAllFilters(w, fields, filters)) : data),
    [data, fields, filters],
  );

  // j/k move a row highlight, Enter/o opens the warehouse detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<Warehouse>({
    items: filtered ?? [],
    onOpen: (w) => navigate(`/inventory/warehouses/${encodeURIComponent(w.code)}`),
    persistKey: "inventory:warehouses",
    getItemId: (w) => w.id,
  });

  // Multi-select for bulk CSV export of the selection (no other bulk verb applies to warehouses).
  const selection = useRowSelection<Warehouse>({
    items: filtered ?? [],
    getItemId: (w) => w.id,
    activeIndex: active,
  });

  // Add is a form (forms keep their controls) — no bar primary, just print + CSV.
  const csvColumns = useMemo<CsvColumn<Warehouse>[]>(
    () => [
      { header: t("inventory.warehouse.code"), accessor: (w) => w.code },
      { header: t("inventory.warehouse.name"), accessor: (w) => w.name },
    ],
    [t],
  );
  useListPageActions({ rows: filtered, columns: csvColumns, filename: "warehouses" });

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [showForm, setShowForm] = useState(false);

  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef, onCancel: () => setShowForm(false) });

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
    setShowForm(false);
  }

  return (
    <section className="inv-page">
      <InventoryNav />

      {!showForm && (
        <button type="button" className="btn btn--sm btn--primary" onClick={() => setShowForm(true)}>
          {t("inventory.warehouse.add")}
        </button>
      )}
      {showForm && (
      <form ref={formRef} className="card inv-toolbar" onSubmit={onSubmit}>
        <label className="inv-field">
          <span>{t("inventory.warehouse.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="inv-field">
          <span>{t("inventory.warehouse.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <button type="button" className="btn btn--sm btn--ghost" onClick={() => setShowForm(false)}>
          {t("common.cancel")}
        </button>
        <button className="btn btn--primary" type="submit">
          {t("inventory.warehouse.add")}
        </button>
      </form>
      )}

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("inventory.warehouse.empty")} hint={t("inventory.warehouse.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="inv-filters">
          <SavedViews api={savedViews} />
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState
          title={t("filter.noMatch")}
          hint={t("filter.noMatchHint")}
          action={{ label: t("filter.clearAll"), onClick: () => setFilters([]) }}
        />
      )}

      {filtered && filtered.length > 0 && (
        <div className="card inv-table-wrap">
          <table className="inv-table">
            <thead>
              <tr>
                <SelectAllCell
                  className="inv-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("inventory.warehouse.code")}</th>
                <th>{t("inventory.warehouse.name")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((w, i) => (
                <tr
                  key={w.id}
                  data-kbd-active={i === active ? "true" : undefined}
                  data-selected={selection.isSelected(w.id) ? "true" : undefined}
                  aria-selected={selection.isSelected(w.id) || i === active}
                >
                  <SelectRowCell
                    className="inv-table__select"
                    checked={selection.isSelected(w.id)}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
                  <td><EntityLink type="warehouse" value={w.code} /></td>
                  <td>{w.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("warehouses-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
