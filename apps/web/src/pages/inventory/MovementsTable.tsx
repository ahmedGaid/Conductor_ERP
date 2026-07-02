import { useTranslation } from "react-i18next";

import type { Movement, MovementType } from "../../api/inventory";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { EntityLink, type EntityType } from "../../components/EntityLink";
import { EmptyState } from "../../components/EmptyState";

// A movement's source document depends on its direction: stock leaving for a customer ties to a sales
// order, stock arriving from a supplier to a purchase order. Transfers/adjustments have no order.
function refType(type: MovementType): EntityType | null {
  if (type === "issue" || type === "return_in") return "salesOrder";
  if (type === "receipt" || type === "return_out") return "purchaseOrder";
  return null;
}

/**
 * Recent stock movements for an item or a warehouse. `show` picks the entity column shown alongside:
 * on the item page we show the warehouse, on the warehouse page we show the item. Every code/number
 * is a click-through (item, warehouse, source order, GL journal).
 */
export function MovementsTable({ movements, show }: { movements: Movement[]; show: "item" | "warehouse" }) {
  const { t } = useTranslation();

  if (movements.length === 0) {
    return <EmptyState title={t("inventory.detail.noMovements")} hint={t("inventory.detail.noMovementsHint")} />;
  }

  return (
    <div className="card inv-table-wrap">
      <table className="inv-table">
        <thead>
          <tr>
            <th>{t("inventory.movement.type")}</th>
            <th>{show === "item" ? t("inventory.warehouse.code") : t("inventory.item.sku")}</th>
            <th className="inv-table__num">{t("inventory.onHand.quantity")}</th>
            <th className="inv-table__num">{t("inventory.onHand.value")}</th>
            <th>{t("inventory.detail.reference")}</th>
            <th>{t("accounting.journals.number")}</th>
          </tr>
        </thead>
        <tbody>
          {movements.map((m) => {
            const order = refType(m.type);
            return (
              <tr key={m.id}>
                <td>{t(`inventory.movement.${m.type}`)}</td>
                <td>
                  {show === "item" ? (
                    <>
                      <EntityLink type="warehouse" value={m.warehouse_code} />
                      {m.dest_warehouse_code && <> → <EntityLink type="warehouse" value={m.dest_warehouse_code} /></>}
                    </>
                  ) : (
                    <EntityLink type="item" value={m.item_sku} />
                  )}
                </td>
                <td className="inv-table__num"><Bdi>{m.quantity}</Bdi></td>
                <td className="inv-table__num"><Bdi>{formatMinor(m.value_minor)}</Bdi></td>
                <td className="latin">
                  {m.reference ? (
                    order ? <EntityLink type={order} value={m.reference} /> : <Bdi>{m.reference}</Bdi>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td className="latin">
                  {m.journal_number ? (
                    <EntityLink type="journal" value={m.journal_number} />
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
