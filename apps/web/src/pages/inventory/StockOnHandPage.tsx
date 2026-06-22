import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { stockOnHand, type StockOnHand } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { FilterBar } from "../../components/FilterBar";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

type StockRow = StockOnHand["rows"][number];

export function StockOnHandPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(stockOnHand, [], "inventory:stock-on-hand");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<StockRow>[]>(
    () => [
      { key: "sku", label: t("inventory.item.sku"), type: "text", accessor: (r) => r.sku },
      { key: "name", label: t("inventory.item.name"), type: "text", accessor: (r) => r.item_name },
      { key: "warehouse", label: t("inventory.warehouse.code"), type: "text", accessor: (r) => r.warehouse_code },
    ],
    [t],
  );
  const rows = useMemo(
    () => (data ? data.rows.filter((r) => matchesAllFilters(r, fields, filters)) : []),
    [data, fields, filters],
  );
  // Keep the footer total honest with the current filter.
  const totalValue = useMemo(() => rows.reduce((s, r) => s + r.value_minor, 0), [rows]);

  return (
    <section className="inv-page">
      <InventoryNav />
      <div className="inv-page__head">
        {data && data.rows.length > 0 && <FilterBar fields={fields} filters={filters} onChange={setFilters} />}
        <Link className="btn btn--primary" to="/inventory/movements">
          {t("inventory.tabs.movements")}
        </Link>
      </div>

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
                  <td><Bdi>{r.sku}</Bdi></td>
                  <td>
                    {r.item_name}
                    {r.below_reorder && <span className="inv-warn"> · {t("inventory.onHand.reorder")}</span>}
                  </td>
                  <td><Bdi>{r.warehouse_code}</Bdi></td>
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
