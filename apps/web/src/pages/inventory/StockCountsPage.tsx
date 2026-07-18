import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { createStockCount, getStockCount, listStockCounts, listWarehouses, type CountStatus } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { useToast } from "../../app/ToastContext";
import { prefetch } from "../../lib/prefetch";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { Badge } from "../../components/Badge";
import { ComboBox } from "../../components/ComboBox";
import { DatePicker } from "../../components/DatePicker";
import { EntityLink } from "../../components/EntityLink";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { InventoryNav } from "./InventoryNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./inventory.css";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

const COUNT_STATUSES: CountStatus[] = ["counting", "posted", "cancelled"];
type StockCount = Awaited<ReturnType<typeof listStockCounts>>[number];

export function StockCountsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(listStockCounts, [], "inventory:counts");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<StockCount>[]>(
    () => [
      { key: "warehouse", label: t("inventory.counts.warehouse"), type: "text", accessor: (c) => c.warehouse_code },
      { key: "date", label: t("inventory.counts.date"), type: "date", accessor: (c) => c.count_date },
      {
        key: "status",
        label: t("inventory.counts.status"),
        type: "select",
        options: COUNT_STATUSES.map((s) => ({ value: s, label: t(`inventory.counts.statuses.${s}`) })),
        accessor: (c) => c.status,
      },
    ],
    [t],
  );
  const savedViews = useSavedViews({ listKey: "inventory:counts", fields, filters, setFilters });
  const filtered = useMemo(
    () => (data ? data.filter((c) => matchesAllFilters(c, fields, filters)) : data),
    [data, fields, filters],
  );

  const statusTabs = useMemo(
    () => COUNT_STATUSES.map((s) => ({ value: s, label: t(`inventory.counts.statuses.${s}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((c) => c.status === tab)) : filtered),
    [filtered, tab],
  );

  // j/k move a row highlight, Enter/o opens it on the detail page.
  const { active } = useListKeyboardNav<StockCount>({
    items: visible ?? [],
    onOpen: (c) => navigate(`/inventory/counts/${c.id}`),
    persistKey: "inventory:counts",
    getItemId: (c) => c.id,
  });

  // Multi-select for bulk CSV export of the selection (posting/cancelling stays on the detail page).
  const selection = useRowSelection<StockCount>({
    items: visible ?? [],
    getItemId: (c) => c.id,
    activeIndex: active,
  });

  // Start-a-count is a form (forms keep their controls) — no bar primary, just print + CSV.
  const csvColumns = useMemo<CsvColumn<StockCount>[]>(
    () => [
      { header: t("inventory.counts.warehouse"), accessor: (c) => c.warehouse_code },
      { header: t("inventory.counts.date"), accessor: (c) => c.count_date },
      { header: t("inventory.counts.lines"), accessor: (c) => c.line_count },
      { header: t("inventory.counts.status"), accessor: (c) => t(`inventory.counts.statuses.${c.status}`) },
    ],
    [t],
  );
  useListPageActions({ rows: visible, columns: csvColumns, filename: "stock-counts" });

  const [warehouse, setWarehouse] = useState("");
  const [countDate, setCountDate] = useState(today());
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!warehouse) {
      setFormError(t("inventory.counts.pickWarehouse"));
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      const count = await createStockCount({ warehouse_code: warehouse, count_date: countDate });
      reload();
      toast.show(t("inventory.toast.countStarted"), "success");
      navigate(`/inventory/counts/${count.id}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="inv-page">
      <InventoryNav />

      <form className="card inv-toolbar" onSubmit={onSubmit}>
        <label className="inv-field">
          <span>{t("inventory.counts.warehouse")}</span>
          <ComboBox
            value={warehouse}
            onChange={setWarehouse}
            placeholder={t("common.selectField", { field: t("inventory.counts.warehouse") })}
            options={(warehouses ?? []).filter((w) => w.is_active).map((w) => ({ value: w.code, label: `${w.code} · ${w.name}` }))}
          />
        </label>
        <label className="inv-field">
          <span>{t("inventory.counts.date")}</span>
          <DatePicker value={countDate} onChange={setCountDate} />
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {t("inventory.counts.start")}
        </button>
      </form>
      <p className="hint">{t("inventory.counts.startHint")}</p>
      {formError && <p className="error-text">{formError}</p>}

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("inventory.counts.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="inv-filters">
          <SavedViews api={savedViews} />
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={statusTabs}
          accessor={(c) => c.status}
          value={tab}
          onChange={setTab}
          ariaLabel={t("inventory.counts.status")}
        />
      )}
      {data && data.length > 0 && visible && visible.length === 0 && (
        <EmptyState
          title={t("filter.noMatch")}
          hint={t("filter.noMatchHint")}
          action={{ label: t("filter.clearAll"), onClick: () => setFilters([]) }}
        />
      )}

      {visible && visible.length > 0 && (
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
                <th>{t("inventory.counts.warehouse")}</th>
                <th>{t("inventory.counts.date")}</th>
                <th className="inv-table__num">{t("inventory.counts.lines")}</th>
                <th>{t("inventory.counts.status")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((c, i) => (
                <tr
                  key={c.id}
                  data-kbd-active={i === active ? "true" : undefined}
                  data-selected={selection.isSelected(c.id) ? "true" : undefined}
                  aria-selected={selection.isSelected(c.id) || i === active}
                >
                  <SelectRowCell
                    className="inv-table__select"
                    checked={selection.isSelected(c.id)}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
                  <td>
                    <Link
                      className="inv-link"
                      to={`/inventory/counts/${c.id}`}
                      onMouseEnter={() => prefetch(`inventory:count:${c.id}`, () => getStockCount(c.id))}
                      onFocus={() => prefetch(`inventory:count:${c.id}`, () => getStockCount(c.id))}
                    >
                      <EntityLink type="warehouse" value={c.warehouse_code} />
                    </Link>
                  </td>
                  <td><Bdi>{c.count_date}</Bdi></td>
                  <td className="inv-table__num"><Bdi>{c.line_count}</Bdi></td>
                  <td>
                    <Badge tone={c.status === "posted" ? "completed" : c.status === "cancelled" ? "failed" : "running"}>
                      {t(`inventory.counts.statuses.${c.status}`)}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("stock-counts-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
