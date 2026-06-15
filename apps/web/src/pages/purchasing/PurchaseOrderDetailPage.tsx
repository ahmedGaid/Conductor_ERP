import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import {
  billPO,
  confirmPO,
  getPurchaseOrder,
  payPO,
  receivePO,
  type PurchaseOrder,
} from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

export function PurchaseOrderDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload } = useAsync<PurchaseOrder>(() => getPurchaseOrder(id as string), [id]);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function run(fn: () => Promise<PurchaseOrder>) {
    setBusy(true);
    setActionError(null);
    try {
      await fn();
      reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="pur-page">
      <h1>{t("nav.purchasing")}</h1>
      <PurchasingNav />

      {loading && <p className="muted">{t("common.loading")}</p>}
      {error && <p className="error-text">{error}</p>}

      {data && (
        <>
          <div className="card pur-page">
            <div className="pur-page__head">
              <div>
                <h2 className="latin">{data.number}</h2>
                <p className="muted">{data.supplier_name} · {data.warehouse_code} · <span className="latin">{data.order_date}</span></p>
              </div>
              <span className={`pur-badge pur-badge--${data.status}`}>{t(`purchasing.status.${data.status}`)}</span>
            </div>

            <div className="pur-summary">
              <div className="pur-summary__item">
                <span className="pur-summary__label">{t("sales.orders.total")}</span>
                <span className="pur-summary__value"><Bdi>{formatMinor(data.subtotal_minor, data.currency)}</Bdi></span>
              </div>
              <div className="pur-summary__item">
                <span className="pur-summary__label">{t("purchasing.detail.billed")}</span>
                <span className="pur-summary__value"><Bdi>{formatMinor(data.billed_minor, data.currency)}</Bdi></span>
              </div>
              <div className="pur-summary__item">
                <span className="pur-summary__label">{t("purchasing.detail.outstanding")}</span>
                <span className="pur-summary__value"><Bdi>{formatMinor(data.outstanding_minor, data.currency)}</Bdi></span>
              </div>
              {data.bill_number && (
                <div className="pur-summary__item">
                  <span className="pur-summary__label">{t("purchasing.detail.billNo")}</span>
                  <span className="latin">{data.bill_number}</span>
                </div>
              )}
            </div>

            <div className="pur-actions">
              {data.status === "draft" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => confirmPO(data.id))}>
                  {t("purchasing.detail.confirm")}
                </button>
              )}
              {data.status === "confirmed" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => receivePO(data.id))}>
                  {t("purchasing.detail.receive")}
                </button>
              )}
              {data.status === "received" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => billPO(data.id))}>
                  {t("purchasing.detail.bill")}
                </button>
              )}
              {data.status === "billed" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => payPO(data.id, data.outstanding_minor))}>
                  {t("purchasing.detail.recordPayment")}
                </button>
              )}
            </div>
            {actionError && <p className="error-text">{actionError}</p>}
          </div>

          <div className="card pur-table-wrap">
            <table className="pur-table">
              <thead>
                <tr>
                  <th>{t("sales.newOrder.item")}</th>
                  <th className="pur-table__num">{t("inventory.onHand.quantity")}</th>
                  <th className="pur-table__num">{t("purchasing.detail.received")}</th>
                  <th className="pur-table__num">{t("purchasing.newOrder.unitCost")}</th>
                  <th className="pur-table__num">{t("sales.orders.total")}</th>
                </tr>
              </thead>
              <tbody>
                {data.lines.map((l) => (
                  <tr key={l.line_no}>
                    <td><Bdi>{l.item_sku}</Bdi>{l.description ? ` · ${l.description}` : ""}</td>
                    <td className="pur-table__num"><Bdi>{l.quantity}</Bdi></td>
                    <td className="pur-table__num"><Bdi>{l.received_qty}</Bdi></td>
                    <td className="pur-table__num"><Bdi>{formatMinor(l.unit_cost_minor)}</Bdi></td>
                    <td className="pur-table__num"><Bdi>{formatMinor(l.line_total_minor)}</Bdi></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
