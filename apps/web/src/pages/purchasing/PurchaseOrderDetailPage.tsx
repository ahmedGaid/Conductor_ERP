import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import {
  approvePO,
  billPO,
  confirmPO,
  getPurchaseOrder,
  payPO,
  receivePO,
  returnPO,
  type POStatus,
  type PurchaseOrder,
} from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { useRecentEntity } from "../../hooks/useRecentEntity";
import { usePaletteActions, type PaletteAction } from "../../app/PaletteActionsContext";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { Disclosure } from "../../components/Disclosure";
import { PurchasingNav } from "./PurchasingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./purchasing.css";

// Plain-language explanation of the current state + next step (human language over the bare status
// word). Display-layer only — the lifecycle is unchanged; the draft+approval case gets its own line.
function statusExplainKey(o: PurchaseOrder): string {
  if (o.status === "draft" && o.requires_approval && !o.approved) return "awaitingApproval";
  return o.status;
}

export function PurchaseOrderDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload, mutate } = useAsync<PurchaseOrder>(
    () => getPurchaseOrder(id as string),
    [id],
    `purchasing:order:${id}`,
  );
  useRecentEntity(data?.number);

  // Optimistic: apply the predicted change (status flip, approval flag) so the badge, explainer
  // and action set update instantly, then let the server's returned order reconcile the derived
  // amounts (billed/outstanding/…). A failure rolls the whole order back and shows an error toast.
  function act(apply: (order: PurchaseOrder) => PurchaseOrder, request: () => Promise<PurchaseOrder>, success: string) {
    if (!data) return;
    void runOptimistic<PurchaseOrder, PurchaseOrder>({
      current: data,
      mutate,
      optimistic: apply,
      request,
      settle: (_predicted, updated) => updated,
      toast,
      success,
    });
  }

  const setStatus = (status: POStatus) => (order: PurchaseOrder): PurchaseOrder => ({ ...order, status });

  // Lifecycle steps mirrored into the ⌘K "This page" group, gated by status exactly as the
  // buttons are, so the palette never offers a step that isn't the real next move.
  const pageActions: PaletteAction[] = [];
  if (data) {
    const s = data.status;
    if (s === "draft" && data.requires_approval && !data.approved) {
      pageActions.push({ id: "approve", label: t("purchasing.detail.approve"),
        run: () => act((o) => ({ ...o, approved: true }), () => approvePO(data.id), t("purchasing.toast.approved")) });
    }
    if (s === "draft" && (!data.requires_approval || data.approved)) {
      pageActions.push({ id: "confirm", label: t("purchasing.detail.confirm"),
        run: () => act(setStatus("confirmed"), () => confirmPO(data.id), t("purchasing.toast.confirmed")) });
    }
    if (s === "confirmed" || s === "partially_received") {
      pageActions.push({ id: "receive",
        label: s === "partially_received" ? t("purchasing.detail.receiveRemaining") : t("purchasing.detail.receive"),
        run: () => act(setStatus("received"), () => receivePO(data.id), t("purchasing.toast.received")) });
    }
    if (s === "received") {
      pageActions.push({ id: "bill", label: t("purchasing.detail.bill"),
        run: () => act(setStatus("billed"), () => billPO(data.id), t("purchasing.toast.billed")) });
    }
    if (s === "billed") {
      pageActions.push({ id: "pay", label: t("purchasing.detail.recordPayment"),
        run: () => act(setStatus("paid"), () => payPO(data.id, data.outstanding_minor), t("purchasing.toast.paid")) });
    }
    if (s === "billed" || s === "paid") {
      pageActions.push({ id: "return", label: t("purchasing.detail.return"),
        run: () => act(setStatus("returned"), () => returnPO(data.id), t("purchasing.toast.returned")) });
    }
  }
  usePaletteActions("po-detail", pageActions);

  return (
    <section className="pur-page">
      <PurchasingNav />

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

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

            <p className="pur-explain">
              {t(`purchasing.statusExplain.${statusExplainKey(data)}`, {
                amount: formatMinor(data.outstanding_minor, data.currency),
              })}
            </p>

            <div className="pur-summary">
              <div className="pur-summary__item">
                <span className="pur-summary__label">{t("sales.orders.total")}</span>
                <span className="pur-summary__value"><Bdi>{formatMinor(data.subtotal_minor, data.currency)}</Bdi></span>
              </div>
              {data.tax_minor > 0 && (
                <div className="pur-summary__item">
                  <span className="pur-summary__label">{t("purchasing.detail.vat")}</span>
                  <span className="pur-summary__value"><Bdi>{formatMinor(data.tax_minor, data.currency)}</Bdi></span>
                </div>
              )}
              <div className="pur-summary__item">
                <span className="pur-summary__label">{t("purchasing.detail.billed")}</span>
                <span className="pur-summary__value"><Bdi>{formatMinor(data.billed_minor, data.currency)}</Bdi></span>
              </div>
              <div className="pur-summary__item">
                <span className="pur-summary__label">{t("purchasing.detail.outstanding")}</span>
                <span className="pur-summary__value"><Bdi>{formatMinor(data.outstanding_minor, data.currency)}</Bdi></span>
              </div>
            </div>

            <div className="pur-actions">
              {data.status === "draft" && data.requires_approval && !data.approved && (
                <button
                  className="btn btn--primary"
                  onClick={() => act((o) => ({ ...o, approved: true }), () => approvePO(data.id), t("purchasing.toast.approved"))}
                >
                  {t("purchasing.detail.approve")}
                </button>
              )}
              {data.status === "draft" && (
                <button
                  // Primary only when it's the actionable next step; while approval is still
                  // pending it stays as a neutral, disabled preview so Approve is the one primary.
                  className={data.requires_approval && !data.approved ? "btn" : "btn btn--primary"}
                  disabled={data.requires_approval && !data.approved}
                  onClick={() => act(setStatus("confirmed"), () => confirmPO(data.id), t("purchasing.toast.confirmed"))}
                >
                  {t("purchasing.detail.confirm")}
                </button>
              )}
              {(data.status === "confirmed" || data.status === "partially_received") && (
                <button
                  className="btn btn--primary"
                  onClick={() => act(setStatus("received"), () => receivePO(data.id), t("purchasing.toast.received"))}
                >
                  {data.status === "partially_received" ? t("purchasing.detail.receiveRemaining") : t("purchasing.detail.receive")}
                </button>
              )}
              {data.status === "received" && (
                <button
                  className="btn btn--primary"
                  onClick={() => act(setStatus("billed"), () => billPO(data.id), t("purchasing.toast.billed"))}
                >
                  {t("purchasing.detail.bill")}
                </button>
              )}
              {data.status === "billed" && (
                <button
                  className="btn btn--primary"
                  onClick={() => act(setStatus("paid"), () => payPO(data.id, data.outstanding_minor), t("purchasing.toast.paid"))}
                >
                  {t("purchasing.detail.recordPayment")}
                </button>
              )}
              {(data.status === "billed" || data.status === "paid") && (
                <button
                  className="btn"
                  onClick={() => act(setStatus("returned"), () => returnPO(data.id), t("purchasing.toast.returned"))}
                >
                  {t("purchasing.detail.return")}
                </button>
              )}
            </div>

            {(data.bill_number || data.debit_note_number || data.returned_minor > 0 || data.requires_approval) && (
              <Disclosure summary={t("common.moreDetails")}>
                <dl className="pur-meta">
                  {data.bill_number && (
                    <div className="pur-meta__row">
                      <dt>{t("purchasing.detail.billNo")}</dt>
                      <dd className="latin">{data.bill_number}</dd>
                    </div>
                  )}
                  {data.debit_note_number && (
                    <div className="pur-meta__row">
                      <dt>{t("purchasing.detail.debitNoteNo")}</dt>
                      <dd className="latin">{data.debit_note_number}</dd>
                    </div>
                  )}
                  {data.returned_minor > 0 && (
                    <div className="pur-meta__row">
                      <dt>{t("purchasing.detail.returned")}</dt>
                      <dd><Bdi>{formatMinor(data.returned_minor, data.currency)}</Bdi></dd>
                    </div>
                  )}
                  {data.requires_approval && (
                    <div className="pur-meta__row">
                      <dt>{t("purchasing.detail.approval")}</dt>
                      <dd>{data.approved ? t("purchasing.detail.approved") : t("purchasing.detail.pendingApproval")}</dd>
                    </div>
                  )}
                </dl>
              </Disclosure>
            )}
          </div>

          <div className="card pur-table-wrap">
            <table className="pur-table">
              <thead>
                <tr>
                  <th>{t("sales.newOrder.item")}</th>
                  <th className="pur-table__num">{t("inventory.onHand.quantity")}</th>
                  <th className="pur-table__num">{t("purchasing.detail.received")}</th>
                  <th className="pur-table__num">{t("purchasing.detail.returnedQty")}</th>
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
                    <td className="pur-table__num"><Bdi>{l.returned_qty}</Bdi></td>
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
