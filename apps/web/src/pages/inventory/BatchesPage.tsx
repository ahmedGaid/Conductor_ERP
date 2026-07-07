import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { listBatches } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { Bdi } from "../../components/Bdi";
import { EntityLink } from "../../components/EntityLink";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { InventoryNav } from "./InventoryNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./inventory.css";

type Batch = Awaited<ReturnType<typeof listBatches>>[number];

function batchId(b: Batch): string {
  return `${b.batch_no}-${b.sku}-${b.warehouse_code}`;
}

export function BatchesPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listBatches, [], "inventory:batches");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<Batch>[]>(
    () => [
      { key: "batch", label: t("inventory.batches.batch"), type: "text", accessor: (b) => b.batch_no },
      { key: "item", label: t("inventory.batches.item"), type: "text", accessor: (b) => `${b.sku} ${b.item_name}` },
      { key: "warehouse", label: t("inventory.batches.warehouse"), type: "text", accessor: (b) => b.warehouse_code },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((b) => matchesAllFilters(b, fields, filters)) : data),
    [data, fields, filters],
  );

  const csvColumns = useMemo<CsvColumn<Batch>[]>(
    () => [
      { header: t("inventory.batches.batch"), accessor: (b) => b.batch_no },
      { header: t("inventory.batches.item"), accessor: (b) => `${b.sku} ${b.item_name}` },
      { header: t("inventory.batches.warehouse"), accessor: (b) => b.warehouse_code },
      { header: t("inventory.batches.received"), accessor: (b) => b.received_quantity },
      { header: t("inventory.batches.expiry"), accessor: (b) => b.earliest_expiry ?? "" },
    ],
    [t],
  );
  useListPageActions({ rows: filtered, columns: csvColumns, filename: "batches" });

  // Multi-select for bulk CSV export (no other bulk verb applies to this read-only reference list;
  // no detail page to open, so no keyboard nav — mouse/Shift-range/⌘A/Esc still work).
  const selection = useRowSelection<Batch>({
    items: filtered ?? [],
    getItemId: batchId,
  });

  return (
    <section className="inv-page">
      <InventoryNav />

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("inventory.batches.empty")} hint={t("inventory.batches.hint")} />
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
                <SelectAllCell
                  className="inv-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("inventory.batches.batch")}</th>
                <th>{t("inventory.batches.item")}</th>
                <th>{t("inventory.batches.warehouse")}</th>
                <th className="inv-table__num">{t("inventory.batches.received")}</th>
                <th>{t("inventory.batches.expiry")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((b, i) => (
                <tr key={batchId(b)} data-selected={selection.isSelected(batchId(b)) ? "true" : undefined} aria-selected={selection.isSelected(batchId(b))}>
                  <SelectRowCell
                    className="inv-table__select"
                    checked={selection.isSelected(batchId(b))}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
                  <td><Bdi>{b.batch_no}</Bdi></td>
                  <td><EntityLink type="item" value={b.sku} /> · {b.item_name}</td>
                  <td><EntityLink type="warehouse" value={b.warehouse_code} /></td>
                  <td className="inv-table__num"><Bdi>{b.received_quantity}</Bdi></td>
                  <td>{b.earliest_expiry ? <Bdi>{b.earliest_expiry}</Bdi> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("batches-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
