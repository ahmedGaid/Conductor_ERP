import { useState } from "react";
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
  type PurchaseOrder,
} from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { Disclosure } from "../../components/Disclosure";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

// Plain-language explanation of the current state + next step (human language over the bare status
// word). Display-layer only — the lifecycle is unchanged; the draft+approval case gets its own line.
function statusExplainKey(o: PurchaseOrder): string {
  if (o.status === "draft" && o.requires_approval && !o.approved) return "awaitingApproval";
  return o.status;
}

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
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => approvePO(data.id))}>
                  {t("purchasing.detail.approve")}
                </button>
              )}
              {data.status === "draft" && (
                <button className="btn btn--primary" disabled={busy || (data.requires_approval && !data.approved)} onClick={() => run(() => confirmPO(data.id))}>
                  {t("purchasing.detail.confirm")}
                </button>
              )}
              {(data.status === "confirmed" || data.status === "partially_received") && (
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => receivePO(data.id))}>
                  {data.status === "partially_received" ? t("purchasing.detail.receiveRemaining") : t("purchasing.detail.receive")}
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
              {(data.status === "billed" || data.status === "paid") && (
                <button className="btn" disabled={busy} onClick={() => run(() => returnPO(data.id))}>
                  {t("purchasing.detail.return")}
                </button>
              )}
            </div>
            {actionError && <p className="error-text">{actionError}</p>}

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
