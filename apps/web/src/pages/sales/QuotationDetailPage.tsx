import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import {
  approveQuotation,
  convertQuotation,
  getQuotation,
  rejectQuotation,
  submitQuotation,
  type Quotation,
  type QuotationStatus,
} from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { Disclosure } from "../../components/Disclosure";
import { SalesNav } from "./SalesNav";
import "./sales.css";

export function QuotationDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload, mutate } = useAsync<Quotation>(
    () => getQuotation(id as string),
    [id],
    `sales:quotation:${id}`,
  );

  // Optimistic state transition: flip the status instantly, reconcile with the server's quotation,
  // roll back + toast on failure.
  function act(nextStatus: QuotationStatus, request: () => Promise<Quotation>, success: string) {
    if (!data) return;
    void runOptimistic<Quotation, Quotation>({
      current: data,
      mutate,
      optimistic: (q) => ({ ...q, status: nextStatus }),
      request,
      settle: (_predicted, updated) => updated,
      toast,
      success,
    });
  }

  // Convert navigates away to the spawned order, so there's no view left to be optimistic about;
  // just route on success and toast on failure.
  async function onConvert(q: Quotation) {
    try {
      const res = await convertQuotation(q.id);
      navigate(`/sales/orders/${res.order_id}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    }
  }

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
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <>
          <div className="card sales-page">
            <div className="sales-page__head">
              <div>
                <h2 className="latin">{data.number}</h2>
                <p className="muted">{data.customer_name} · {data.warehouse_code} · <span className="latin">{data.quote_date}</span></p>
              </div>
              <span className={`sales-badge sales-badge--${data.status}`}>{t(`sales.quotationStatus.${data.status}`)}</span>
            </div>

            <div className="sales-summary">
              <div className="sales-summary__item">
                <span className="sales-summary__label">{t("sales.orders.total")}</span>
                <span className="sales-summary__value"><Bdi>{formatMinor(data.subtotal_minor, data.currency)}</Bdi></span>
              </div>
            </div>

            <div className="sales-actions">
              {data.status === "draft" && (
                <button
                  className="btn btn--primary"
                  onClick={() => act("submitted", () => submitQuotation(data.id), t("sales.toast.quoteSubmitted"))}
                >
                  {t("sales.quotations.submit")}
                </button>
              )}
              {data.status === "submitted" && (
                <button
                  className="btn btn--primary"
                  onClick={() => act("approved", () => approveQuotation(data.id), t("sales.toast.quoteApproved"))}
                >
                  {t("sales.quotations.approve")}
                </button>
              )}
              {data.status === "approved" && (
                <button className="btn btn--primary" onClick={() => onConvert(data)}>
                  {t("sales.quotations.convert")}
                </button>
              )}
              {(data.status === "submitted" || data.status === "approved") && (
                <button
                  className="btn"
                  onClick={() => act("rejected", () => rejectQuotation(data.id, ""), t("sales.toast.quoteRejected"))}
                >
                  {t("sales.quotations.reject")}
                </button>
              )}
            </div>

            <Disclosure summary={t("common.moreDetails")}>
              <dl className="sales-meta">
                <div className="sales-meta__row">
                  <dt>{t("sales.quotations.approval")}</dt>
                  <dd>{data.requires_approval ? t("sales.quotations.needsApproval") : t("sales.quotations.autoApprove")}</dd>
                </div>
                {data.converted_order_number && (
                  <div className="sales-meta__row">
                    <dt>{t("sales.quotations.convertedTo")}</dt>
                    <dd className="latin">{data.converted_order_number}</dd>
                  </div>
                )}
                {data.rejected_reason && (
                  <div className="sales-meta__row">
                    <dt>{t("sales.quotations.rejectedReason")}</dt>
                    <dd>{data.rejected_reason}</dd>
                  </div>
                )}
              </dl>
            </Disclosure>
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
