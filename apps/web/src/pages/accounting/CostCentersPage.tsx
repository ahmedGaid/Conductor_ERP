import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createCostCenter, listCostCenters } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { useFormKeys } from "../../hooks/useFormKeys";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./accounting.css";

type CostCenter = Awaited<ReturnType<typeof listCostCenters>>[number];

export function CostCentersPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(listCostCenters, [], "accounting:cost-centers");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<CostCenter>[]>(
    () => [
      { key: "code", label: t("accounting.costCenters.code"), type: "text", accessor: (cc) => cc.code },
      { key: "name", label: t("accounting.costCenters.name"), type: "text", accessor: (cc) => cc.name },
    ],
    [t],
  );
  const savedViews = useSavedViews({ listKey: "accounting:cost-centers", fields, filters, setFilters });
  const filtered = useMemo(
    () => (data ? data.filter((cc) => matchesAllFilters(cc, fields, filters)) : data),
    [data, fields, filters],
  );

  // Add is a form (forms keep their controls) — no bar primary, just print + CSV.
  const csvColumns = useMemo<CsvColumn<CostCenter>[]>(
    () => [
      { header: t("accounting.costCenters.code"), accessor: (cc) => cc.code },
      { header: t("accounting.costCenters.name"), accessor: (cc) => cc.name },
      { header: t("accounting.costCenters.active"), accessor: (cc) => (cc.is_active ? t("common.yes") : t("common.no")) },
    ],
    [t],
  );
  useListPageActions({ rows: filtered, columns: csvColumns, filename: "cost-centers" });

  // Multi-select for bulk CSV export (no other bulk verb applies; no detail page, so no keyboard nav).
  const selection = useRowSelection<CostCenter>({
    items: filtered ?? [],
    getItemId: (cc) => cc.id,
  });

  const [code, setCode] = useState("");
  const [name, setName] = useState("");

  // ⌘/Ctrl+Enter submits the add form from any field.
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

  // Optimistic create: show the new cost center instantly and clear the form for the next entry; the
  // server row replaces the placeholder on settle, or it rolls back + toasts.
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const c = code.trim();
    const n = name.trim();
    if (!c || !n) return;
    void optimisticCreate<CostCenter>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, code: c, name: n, is_active: true }) as CostCenter,
      request: () => createCostCenter({ code: c, name: n }),
      toast,
      success: t("accounting.toast.costCenterCreated"),
    });
    setCode("");
    setName("");
  }

  return (
    <section className="acct-page">
      <AccountingNav />

      <form ref={formRef} className="card acct-toolbar" onSubmit={onSubmit}>
        <label className="acct-field">
          <span>{t("accounting.costCenters.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="acct-field grow">
          <span>{t("accounting.costCenters.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <button className="btn btn--primary" type="submit">
          {t("accounting.costCenters.add")}
        </button>
      </form>

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("accounting.costCenters.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="acct-filters">
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
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <SelectAllCell
                  className="acct-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("accounting.costCenters.code")}</th>
                <th>{t("accounting.costCenters.name")}</th>
                <th>{t("accounting.costCenters.active")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((cc, i) => (
                <tr key={cc.id} data-selected={selection.isSelected(cc.id) ? "true" : undefined} aria-selected={selection.isSelected(cc.id)}>
                  <SelectRowCell
                    className="acct-table__select"
                    checked={selection.isSelected(cc.id)}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
                  <td><Bdi>{cc.code}</Bdi></td>
                  <td>{cc.name}</td>
                  <td>{cc.is_active ? t("common.yes") : t("common.no")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("cost-centers-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
