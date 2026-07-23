import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { listBatches } from "../../api/inventory";
import { Badge, type BadgeTone } from "../../components/Badge";
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
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
import { InventoryNav } from "./InventoryNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./inventory.css";

type Batch = Awaited<ReturnType<typeof listBatches>>[number];

function batchId(b: Batch): string {
  return `${b.batch_no}-${b.sku}-${b.warehouse_code}`;
}

const MS_PER_DAY = 1000 * 60 * 60 * 24;

function daysUntil(dateStr: string): number {
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / MS_PER_DAY);
}

function expiryTone(days: number): BadgeTone {
  if (days < 0) return "failed";
  if (days <= 30) return "waiting";
  return "neutral";
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
      { key: "expiry", label: t("inventory.batches.expiry"), type: "date", accessor: (b) => b.earliest_expiry ?? "" },
    ],
    [t],
  );
  const savedViews = useSavedViews({ listKey: "inventory:batches", fields, filters, setFilters });
  // Soonest-expiring first (the question this screen exists to answer); rows with no expiry sort last.
  const filtered = useMemo(
    () =>
      data
        ?.filter((b) => matchesAllFilters(b, fields, filters))
        .slice()
        .sort((a, b) => (a.earliest_expiry ?? "9999").localeCompare(b.earliest_expiry ?? "9999")),
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
                <th>{t("inventory.batches.batch")}</th>
                <th>{t("inventory.batches.item")}</th>
                <th>{t("inventory.batches.warehouse")}</th>
                <th className="inv-table__num">{t("inventory.batches.received")}</th>
                <th>{t("inventory.batches.expiry")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((b, i) => {
                const days = b.earliest_expiry ? daysUntil(b.earliest_expiry) : null;
                return (
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
                    <td>
                      {b.earliest_expiry && days !== null ? (
                        <span className="inv-batch-expiry">
                          <Bdi>{b.earliest_expiry}</Bdi>
                          <Badge tone={expiryTone(days)}>
                            {days < 0
                              ? t("inventory.batches.expiredAgo", { count: Math.abs(days) })
                              : days === 0
                                ? t("inventory.batches.expiresToday")
                                : t("inventory.batches.expiresIn", { count: days })}
                          </Badge>
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <Link className="btn btn--sm btn--ghost" to={`/inventory/stock-on-hand?sku=${encodeURIComponent(b.sku)}`}>
                        {t("inventory.batches.viewStock")}
                      </Link>
                    </td>
                  </tr>
                );
              })}
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
