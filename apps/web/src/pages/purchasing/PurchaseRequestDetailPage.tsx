import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import {
  approveRequest,
  convertRequest,
  getRequest,
  rejectRequest,
  submitRequest,
  type PurchaseRequest,
} from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { Disclosure } from "../../components/Disclosure";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

export function PurchaseRequestDetailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload } = useAsync<PurchaseRequest>(() => getRequest(id as string), [id]);
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

  async function onConvert(r: PurchaseRequest) {
    setBusy(true);
    setActionError(null);
    try {
      const res = await convertRequest(r.id);
      navigate(`/purchasing/orders/${res.order_id}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <section className="pur-page">
      <PurchasingNav />

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
          <div className="card pur-page">
            <div className="pur-page__head">
              <div>
                <h2 className="latin">{data.number}</h2>
                <p className="muted">{data.supplier_name} · {data.warehouse_code} · <span className="latin">{data.request_date}</span></p>
              </div>
              <span className={`pur-badge pur-badge--${data.status}`}>{t(`purchasing.requestStatus.${data.status}`)}</span>
            </div>

            <div className="pur-summary">
              <div className="pur-summary__item">
                <span className="pur-summary__label">{t("sales.orders.total")}</span>
                <span className="pur-summary__value"><Bdi>{formatMinor(data.subtotal_minor, data.currency)}</Bdi></span>
              </div>
            </div>

            <div className="pur-actions">
              {data.status === "draft" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => submitRequest(data.id))}>
                  {t("purchasing.requests.submit")}
                </button>
              )}
              {data.status === "submitted" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => approveRequest(data.id))}>
                  {t("purchasing.requests.approve")}
                </button>
              )}
              {data.status === "approved" && (
                <button className="btn btn--primary" disabled={busy} onClick={() => onConvert(data)}>
                  {t("purchasing.requests.convert")}
                </button>
              )}
              {(data.status === "submitted" || data.status === "approved") && (
                <button className="btn" disabled={busy} onClick={() => run(() => rejectRequest(data.id, ""))}>
                  {t("purchasing.requests.reject")}
                </button>
              )}
            </div>
            {actionError && <p className="error-text">{actionError}</p>}

            <Disclosure summary={t("common.moreDetails")}>
              <dl className="pur-meta">
                <div className="pur-meta__row">
                  <dt>{t("purchasing.requests.approval")}</dt>
                  <dd>{data.requires_approval ? t("purchasing.requests.needsApproval") : t("purchasing.requests.autoApprove")}</dd>
                </div>
                {data.converted_order_number && (
                  <div className="pur-meta__row">
                    <dt>{t("purchasing.requests.convertedTo")}</dt>
                    <dd className="latin">{data.converted_order_number}</dd>
                  </div>
                )}
                {data.rejected_reason && (
                  <div className="pur-meta__row">
                    <dt>{t("purchasing.requests.rejectedReason")}</dt>
                    <dd>{data.rejected_reason}</dd>
                  </div>
                )}
              </dl>
            </Disclosure>
          </div>

          <div className="card pur-table-wrap">
            <table className="pur-table">
              <thead>
                <tr>
                  <th>{t("sales.newOrder.item")}</th>
                  <th className="pur-table__num">{t("inventory.onHand.quantity")}</th>
                  <th className="pur-table__num">{t("purchasing.newOrder.unitCost")}</th>
                  <th className="pur-table__num">{t("sales.orders.total")}</th>
                </tr>
              </thead>
              <tbody>
                {data.lines.map((l) => (
                  <tr key={l.line_no}>
                    <td><Bdi>{l.item_sku}</Bdi>{l.description ? ` · ${l.description}` : ""}</td>
                    <td className="pur-table__num"><Bdi>{l.quantity}</Bdi></td>
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
