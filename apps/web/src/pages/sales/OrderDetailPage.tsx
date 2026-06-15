import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import {
  confirmOrder,
  deliverOrder,
  getOrder,
  invoiceOrder,
  payOrder,
  type SalesOrder,
} from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { SalesNav } from "./SalesNav";
import "./sales.css";

export function OrderDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload } = useAsync<SalesOrder>(() => getOrder(id as string), [id]);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function run(fn: () => Promise<SalesOrder>) {
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
    <section className="sales-page">
      <h1>{t("nav.sales")}</h1>
      <SalesNav />

      {loading && <p className="muted">{t("common.loading")}</p>}
      {error && <p className="error-text">{error}</p>}

      {data && (
        <>
          <div className="card sales-page">
            <div className="sales-page__head">
              <div>
                <h2 className="latin">{data.number}</h2>
                <p className="muted">{data.customer_name} · {data.warehouse_code} · <span className="latin">{data.order_date}</span></p>
              </div>
              <span className={`sales-badge sales-badge--${data.status}`}>{t(`sales.status.${data.status}`)}</span>
            </div>

            <div className="sales-summary">
              <div className="sales-summary__item">
                <span className="sales-summary__label">{t("sales.orders.total")}</span>
                <span className="sales-summary__value"><Bdi>{formatMinor(data.subtotal_minor, data.currency)}</Bdi></span>
              </div>
              <div className="sales-summary__item">
                <span className="sales-summary__label">{t("sales.detail.invoiced")}</span>
                <span className="sales-summary__value"><Bdi>{formatMinor(data.invoiced_minor, data.currency)}</Bdi></span>
              </div>
              <div className="sales-summary__item">
                <span className="sales-summary__label">{t("sales.detail.outstanding")}</span>
                <span className="sales-summary__value"><Bdi>{formatMinor(data.outstanding_minor, data.currency)}</Bdi></span>
              </div>
              {data.invoice_number && (
                <div className="sales-summary__item">
                  <span className="sales-summary__label">{t("sales.detail.invoiceNo")}</span>
                  <span className="latin">{data.invoice_number}</span>
                </div>
              )}
            </div>

            <div className="sales-actions">
              {data.status === "draft" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => confirmOrder(data.id))}>
                  {t("sales.detail.confirm")}
                </button>
              )}
              {data.status === "confirmed" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => deliverOrder(data.id))}>
                  {t("sales.detail.deliver")}
                </button>
              )}
              {data.status === "delivered" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => invoiceOrder(data.id))}>
                  {t("sales.detail.invoice")}
                </button>
              )}
              {data.status === "invoiced" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => payOrder(data.id, data.outstanding_minor))}>
                  {t("sales.detail.recordPayment")}
                </button>
              )}
            </div>
            {actionError && <p className="error-text">{actionError}</p>}
          </div>

          <div className="card sales-table-wrap">
            <table className="sales-table">
              <thead>
                <tr>
                  <th>{t("sales.newOrder.item")}</th>
                  <th className="sales-table__num">{t("inventory.onHand.quantity")}</th>
                  <th className="sales-table__num">{t("sales.newOrder.unitPrice")}</th>
                  <th className="sales-table__num">{t("sales.orders.total")}</th>
                </tr>
              </thead>
              <tbody>
                {data.lines.map((l) => (
                  <tr key={l.line_no}>
                    <td><Bdi>{l.item_sku}</Bdi>{l.description ? ` · ${l.description}` : ""}</td>
                    <td className="sales-table__num"><Bdi>{l.quantity}</Bdi></td>
                    <td className="sales-table__num"><Bdi>{formatMinor(l.unit_price_minor)}</Bdi></td>
                    <td className="sales-table__num"><Bdi>{formatMinor(l.line_total_minor)}</Bdi></td>
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
