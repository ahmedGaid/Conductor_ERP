import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import {
  approveRequest,
  convertRequest,
  getRequest,
  rejectRequest,
  submitRequest,
  type PRStatus,
  type PurchaseRequest,
} from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { Disclosure } from "../../components/Disclosure";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

export function PurchaseRequestDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload, mutate } = useAsync<PurchaseRequest>(
    () => getRequest(id as string),
    [id],
    `purchasing:request:${id}`,
  );

  // Optimistic state transition: flip the status instantly, reconcile with the server's request,
  // roll back + toast on failure.
  function act(nextStatus: PRStatus, request: () => Promise<PurchaseRequest>, success: string) {
    if (!data) return;
    void runOptimistic<PurchaseRequest, PurchaseRequest>({
      current: data,
      mutate,
      optimistic: (r) => ({ ...r, status: nextStatus }),
      request,
      settle: (_predicted, updated) => updated,
      toast,
      success,
    });
  }

  // Convert navigates away to the spawned order, so there's no view left to be optimistic about;
  // just route on success and toast on failure.
  async function onConvert(r: PurchaseRequest) {
    try {
      const res = await convertRequest(r.id);
      navigate(`/purchasing/orders/${res.order_id}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
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
      {error && <ErrorState message={error} onRetry={reload} />}

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
                <button
                  className="btn btn--primary"
                  onClick={() => act("submitted", () => submitRequest(data.id), t("purchasing.toast.reqSubmitted"))}
                >
                  {t("purchasing.requests.submit")}
                </button>
              )}
              {data.status === "submitted" && (
                <button
                  className="btn btn--primary"
                  onClick={() => act("approved", () => approveRequest(data.id), t("purchasing.toast.reqApproved"))}
                >
                  {t("purchasing.requests.approve")}
                </button>
              )}
              {data.status === "approved" && (
                <button className="btn btn--primary" onClick={() => onConvert(data)}>
                  {t("purchasing.requests.convert")}
                </button>
              )}
              {(data.status === "submitted" || data.status === "approved") && (
                <button
                  className="btn"
                  onClick={() => act("rejected", () => rejectRequest(data.id, ""), t("purchasing.toast.reqRejected"))}
                >
                  {t("purchasing.requests.reject")}
                </button>
              )}
            </div>

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
