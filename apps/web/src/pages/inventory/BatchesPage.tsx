import { useTranslation } from "react-i18next";

import { listBatches } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

export function BatchesPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(listBatches, [], "inventory:batches");

  return (
    <section className="inv-page">
      <h1>{t("nav.inventory")}</h1>
      <InventoryNav />

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}

      {data && data.length === 0 && (
        <EmptyState title={t("inventory.batches.empty")} hint={t("inventory.batches.hint")} />
      )}

      {data && data.length > 0 && (
        <div className="card inv-table-wrap">
          <table className="inv-table">
            <thead>
              <tr>
                <th>{t("inventory.batches.batch")}</th>
                <th>{t("inventory.batches.item")}</th>
                <th>{t("inventory.batches.warehouse")}</th>
                <th className="inv-table__num">{t("inventory.batches.received")}</th>
                <th>{t("inventory.batches.expiry")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((b, i) => (
                <tr key={`${b.batch_no}-${b.sku}-${b.warehouse_code}-${i}`}>
                  <td><Bdi>{b.batch_no}</Bdi></td>
                  <td><Bdi>{b.sku}</Bdi> · {b.item_name}</td>
                  <td><Bdi>{b.warehouse_code}</Bdi></td>
                  <td className="inv-table__num"><Bdi>{b.received_quantity}</Bdi></td>
                  <td>{b.earliest_expiry ? <Bdi>{b.earliest_expiry}</Bdi> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
