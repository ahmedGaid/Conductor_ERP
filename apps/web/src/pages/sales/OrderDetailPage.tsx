import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import {
  approveOrder,
  confirmOrder,
  deliverOrder,
  getOrder,
  invoiceOrder,
  payOrder,
  returnOrder,
  type OrderStatus,
  type SalesOrder,
} from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { Disclosure } from "../../components/Disclosure";
import { SalesNav } from "./SalesNav";
import "./sales.css";

// Plain-language explanation of the current state and the next step (human language over the bare
// status word). Display-layer only — the status enum/lifecycle is unchanged. The draft+approval
// case gets its own "waiting for approval" message; everything else maps from the status.
function statusExplainKey(o: SalesOrder): string {
  if (o.status === "draft" && o.requires_approval && !o.approved) return "awaitingApproval";
  return o.status;
}

export function OrderDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, mutate } = useAsync<SalesOrder>(
    () => getOrder(id as string),
    [id],
    `sales:order:${id}`,
  );

  // Optimistic: apply the predicted change (status flip, approval flag) so the badge, explainer
  // and action set update instantly, then let the server's returned order reconcile the derived
  // amounts (invoiced/outstanding/…). A failure rolls the whole order back and shows an error toast.
  function act(apply: (order: SalesOrder) => SalesOrder, request: () => Promise<SalesOrder>, success: string) {
    if (!data) return;
    void runOptimistic<SalesOrder, SalesOrder>({
      current: data,
      mutate,
      optimistic: apply,
      request,
      settle: (_predicted, updated) => updated,
      toast,
      success,
    });
  }

  const setStatus = (status: OrderStatus) => (order: SalesOrder): SalesOrder => ({ ...order, status });

  return (
    <section className="sales-page">
      <SalesNav />

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
        <>
          <div className="card sales-page">
            <div className="sales-page__head">
              <div>
                <h2 className="latin">{data.number}</h2>
                <p className="muted">{data.customer_name} · {data.warehouse_code} · <span className="latin">{data.order_date}</span></p>
              </div>
              <span className={`sales-badge sales-badge--${data.status}`}>{t(`sales.status.${data.status}`)}</span>
            </div>

            <p className="sales-explain">
              {t(`sales.statusExplain.${statusExplainKey(data)}`, {
                amount: formatMinor(data.outstanding_minor, data.currency),
              })}
            </p>

            <div className="sales-summary">
              <div className="sales-summary__item">
                <span className="sales-summary__label">{t("sales.orders.total")}</span>
                <span className="sales-summary__value"><Bdi>{formatMinor(data.subtotal_minor, data.currency)}</Bdi></span>
              </div>
              {data.tax_minor > 0 && (
                <div className="sales-summary__item">
                  <span className="sales-summary__label">{t("sales.detail.vat")}{data.tax_code ? ` (${data.tax_code})` : ""}</span>
                  <span className="sales-summary__value"><Bdi>{formatMinor(data.tax_minor, data.currency)}</Bdi></span>
                </div>
              )}
              <div className="sales-summary__item">
                <span className="sales-summary__label">{t("sales.detail.invoiced")}</span>
                <span className="sales-summary__value"><Bdi>{formatMinor(data.invoiced_minor, data.currency)}</Bdi></span>
              </div>
              <div className="sales-summary__item">
                <span className="sales-summary__label">{t("sales.detail.outstanding")}</span>
                <span className="sales-summary__value"><Bdi>{formatMinor(data.outstanding_minor, data.currency)}</Bdi></span>
              </div>
            </div>

            <div className="sales-actions">
              {data.status === "draft" && data.requires_approval && !data.approved && (
                <button
                  className="btn btn--primary"
                  onClick={() => act((o) => ({ ...o, approved: true }), () => approveOrder(data.id), t("sales.toast.approved"))}
                >
                  {t("sales.detail.approve")}
                </button>
              )}
              {data.status === "draft" && (
                <button
                  className="btn btn--primary"
                  disabled={data.requires_approval && !data.approved}
                  onClick={() => act(setStatus("confirmed"), () => confirmOrder(data.id), t("sales.toast.confirmed"))}
                >
                  {t("sales.detail.confirm")}
                </button>
              )}
              {(data.status === "confirmed" || data.status === "partially_delivered") && (
                <button
                  className="btn btn--primary"
                  onClick={() => act(setStatus("delivered"), () => deliverOrder(data.id), t("sales.toast.delivered"))}
                >
                  {data.status === "partially_delivered" ? t("sales.detail.deliverRemaining") : t("sales.detail.deliver")}
                </button>
              )}
              {data.status === "delivered" && (
                <button
                  className="btn btn--primary"
                  onClick={() => act(setStatus("invoiced"), () => invoiceOrder(data.id), t("sales.toast.invoiced"))}
                >
                  {t("sales.detail.invoice")}
                </button>
              )}
              {data.status === "invoiced" && (
                <button
                  className="btn btn--primary"
                  onClick={() => act(setStatus("paid"), () => payOrder(data.id, data.outstanding_minor), t("sales.toast.paid"))}
                >
                  {t("sales.detail.recordPayment")}
                </button>
              )}
              {(data.status === "invoiced" || data.status === "paid") && (
                <button
                  className="btn"
                  onClick={() => act(setStatus("returned"), () => returnOrder(data.id), t("sales.toast.returned"))}
                >
                  {t("sales.detail.return")}
                </button>
              )}
            </div>

            {(data.invoice_number || data.credit_note_number || data.returned_minor > 0 || data.requires_approval) && (
              <Disclosure summary={t("common.moreDetails")}>
                <dl className="sales-meta">
                  {data.invoice_number && (
                    <div className="sales-meta__row">
                      <dt>{t("sales.detail.invoiceNo")}</dt>
                      <dd className="latin">{data.invoice_number}</dd>
                    </div>
                  )}
                  {data.credit_note_number && (
                    <div className="sales-meta__row">
                      <dt>{t("sales.detail.creditNoteNo")}</dt>
                      <dd className="latin">{data.credit_note_number}</dd>
                    </div>
                  )}
                  {data.returned_minor > 0 && (
                    <div className="sales-meta__row">
                      <dt>{t("sales.detail.returned")}</dt>
                      <dd><Bdi>{formatMinor(data.returned_minor, data.currency)}</Bdi></dd>
                    </div>
                  )}
                  {data.requires_approval && (
                    <div className="sales-meta__row">
                      <dt>{t("sales.detail.approval")}</dt>
                      <dd>{data.approved ? t("sales.detail.approved") : t("sales.detail.pendingApproval")}</dd>
                    </div>
                  )}
                </dl>
              </Disclosure>
            )}
          </div>

          <div className="card sales-table-wrap">
            <table className="sales-table">
              <thead>
                <tr>
                  <th>{t("sales.newOrder.item")}</th>
                  <th className="sales-table__num">{t("inventory.onHand.quantity")}</th>
                  <th className="sales-table__num">{t("sales.detail.delivered")}</th>
                  <th className="sales-table__num">{t("sales.detail.returnedQty")}</th>
                  <th className="sales-table__num">{t("sales.newOrder.unitPrice")}</th>
                  <th className="sales-table__num">{t("sales.newOrder.discount")}</th>
                  <th className="sales-table__num">{t("sales.orders.total")}</th>
                </tr>
              </thead>
              <tbody>
                {data.lines.map((l) => (
                  <tr key={l.line_no}>
                    <td><Bdi>{l.item_sku}</Bdi>{l.description ? ` · ${l.description}` : ""}</td>
                    <td className="sales-table__num"><Bdi>{l.quantity}</Bdi></td>
                    <td className="sales-table__num"><Bdi>{l.delivered_qty}</Bdi></td>
                    <td className="sales-table__num"><Bdi>{l.returned_qty}</Bdi></td>
                    <td className="sales-table__num"><Bdi>{formatMinor(l.unit_price_minor)}</Bdi></td>
                    <td className="sales-table__num"><Bdi>{formatMinor(l.discount_minor)}</Bdi></td>
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
