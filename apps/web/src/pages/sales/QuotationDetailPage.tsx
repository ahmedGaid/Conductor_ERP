import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import {
  approveQuotation,
  convertQuotation,
  getQuotation,
  rejectQuotation,
  submitQuotation,
  type Quotation,
} from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { Disclosure } from "../../components/Disclosure";
import { SalesNav } from "./SalesNav";
import "./sales.css";

export function QuotationDetailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload } = useAsync<Quotation>(() => getQuotation(id as string), [id]);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function run(fn: () => Promise<unknown>) {
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

  async function onConvert(q: Quotation) {
    setBusy(true);
    setActionError(null);
    try {
      const res = await convertQuotation(q.id);
      navigate(`/sales/orders/${res.order_id}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
      setBusy(false);
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
      {error && <p className="error-text">{error}</p>}

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
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => submitQuotation(data.id))}>
                  {t("sales.quotations.submit")}
                </button>
              )}
              {data.status === "submitted" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => approveQuotation(data.id))}>
                  {t("sales.quotations.approve")}
                </button>
              )}
              {data.status === "approved" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => onConvert(data)}>
                  {t("sales.quotations.convert")}
                </button>
              )}
              {(data.status === "submitted" || data.status === "approved") && (
                <button className="btn" disabled={busy} onClick={() => run(() => rejectQuotation(data.id, ""))}>
                  {t("sales.quotations.reject")}
                </button>
              )}
            </div>
            {actionError && <p className="error-text">{actionError}</p>}

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
