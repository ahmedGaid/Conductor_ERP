import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { stockOnHand } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

export function StockOnHandPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(stockOnHand, [], "inventory:stock-on-hand");

  return (
    <section className="inv-page">
      <InventoryNav />
      <div className="inv-page__head">
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
              {data.rows.map((r) => (
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
              {data.rows.length === 0 && (
                <tr><td colSpan={6} className="muted">{t("inventory.onHand.empty")}</td></tr>
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={5}>{t("inventory.onHand.totalValue")}</td>
                <td className="inv-table__num"><Bdi>{formatMinor(data.total_value_minor)}</Bdi></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </section>
  );
}
