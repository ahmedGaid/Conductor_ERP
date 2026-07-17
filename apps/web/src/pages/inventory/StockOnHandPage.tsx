import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";

import { stockOnHand, type StockOnHand } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { formatMinor } from "../../lib/money";
import { useListPageActions } from "../../hooks/useListPageActions";
import type { CsvColumn } from "../../lib/csvExport";
import { matchesAllFilters, filtersFromParams, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EntityLink } from "../../components/EntityLink";
import { FilterBar } from "../../components/FilterBar";
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
import { InventoryNav } from "./InventoryNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./inventory.css";

type StockRow = StockOnHand["rows"][number];

export function StockOnHandPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(stockOnHand, [], "inventory:stock-on-hand");
  const [searchParams] = useSearchParams();

  const fields = useMemo<FilterField<StockRow>[]>(
    () => [
      { key: "sku", label: t("inventory.item.sku"), type: "text", accessor: (r) => r.sku },
      { key: "name", label: t("inventory.item.name"), type: "text", accessor: (r) => r.item_name },
      { key: "warehouse", label: t("inventory.warehouse.code"), type: "text", accessor: (r) => r.warehouse_code },
    ],
    [t],
  );

  // Seed the filter chips from the URL once, so a drill-in link (an item row → `/inventory?sku=…`)
  // opens this list pre-filtered; the chip is then freely editable like any other.
  const [filters, setFilters] = useState<ActiveFilter[]>(() => filtersFromParams(searchParams, fields));
  const savedViews = useSavedViews({ listKey: "inventory:stock-on-hand", fields, filters, setFilters });
  const rows = useMemo(
    () => (data ? data.rows.filter((r) => matchesAllFilters(r, fields, filters)) : []),
    [data, fields, filters],
  );
  // Keep the footer total honest with the current filter.
  const totalValue = useMemo(() => rows.reduce((s, r) => s + r.value_minor, 0), [rows]);

  const csvColumns = useMemo<CsvColumn<StockRow>[]>(
    () => [
      { header: t("inventory.item.sku"), accessor: (r) => r.sku },
      { header: t("inventory.item.name"), accessor: (r) => r.item_name },
      { header: t("inventory.warehouse.code"), accessor: (r) => r.warehouse_code },
      { header: t("inventory.onHand.quantity"), accessor: (r) => r.quantity },
      { header: t("inventory.onHand.avgCost"), accessor: (r) => formatMinor(r.avg_cost_minor) },
      { header: t("inventory.onHand.value"), accessor: (r) => formatMinor(r.value_minor) },
    ],
    [t],
  );
  const listPrimary = useMemo(
    () => ({ label: t("inventory.tabs.movements"), onClick: () => navigate("/inventory/movements") }),
    [t, navigate],
  );
  useListPageActions({ primary: listPrimary, rows, columns: csvColumns, filename: "stock-on-hand" });

  return (
    <section className="inv-page">
      <InventoryNav />
      <div className="inv-page__head">
        {data && data.rows.length > 0 && (
          <>
            <SavedViews api={savedViews} />
            <FilterBar fields={fields} filters={filters} onChange={setFilters} />
          </>
        )}
      </div>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <div className="card inv-table-wrap">
          <table className="inv-table">
            <thead>
              <tr>
                <th>{t("inventory.item.sku")}</th>
                <th>{t("inventory.item.name")}</th>
                <th>{t("inventory.warehouse.code")}</th>
                <th className="inv-table__num">{t("inventory.onHand.quantity")}</th>
                <th className="inv-table__num">{t("inventory.onHand.avgCost")}</th>
                <th className="inv-table__num">{t("inventory.onHand.value")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.sku}-${r.warehouse_code}`}>
                  <td><EntityLink type="item" value={r.sku} /></td>
                  <td>
                    {r.item_name}
                    {r.below_reorder && <span className="inv-warn"> · {t("inventory.onHand.reorder")}</span>}
                  </td>
                  <td><EntityLink type="warehouse" value={r.warehouse_code} /></td>
                  <td className="inv-table__num"><Bdi>{r.quantity}</Bdi></td>
                  <td className="inv-table__num"><Bdi>{formatMinor(r.avg_cost_minor)}</Bdi></td>
                  <td className="inv-table__num"><Bdi>{formatMinor(r.value_minor)}</Bdi></td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="muted">
                    {data.rows.length === 0 ? t("inventory.onHand.empty") : t("filter.noMatch")}
                  </td>
                </tr>
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={5}>{t("inventory.onHand.totalValue")}</td>
                <td className="inv-table__num"><Bdi>{formatMinor(totalValue)}</Bdi></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </section>
  );
}
