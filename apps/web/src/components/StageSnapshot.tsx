import { useTranslation } from "react-i18next";

import type { StageDocs, StageHistoryEntry, WorkflowKind } from "../lib/workflow";
import { formatMinor } from "../lib/money";
import { movementsForReference, type Movement } from "../api/inventory";
import { useAsync } from "../hooks/useAsync";
import { Bdi } from "./Bdi";
import { EntityLink } from "./EntityLink";
import { NavIcon } from "../app/icons";
import "./stageSnapshot.css";

/**
 * StageSnapshot — the panel opened when a workflow tracker stage is clicked. It leads with the live
 * documents that stage produced — the invoice/bill GL journal, or the stock movements of the
 * delivery/receipt — so the user can jump straight to the real record. Then, when an audit-trail
 * snapshot exists, it shows the order exactly as it was at that point (party, warehouse, lines,
 * totals). Read-only; monochrome chrome with the module accent only on links.
 */
export function StageSnapshot({
  kind,
  stageKey,
  entry,
  docs,
  onClose,
}: {
  kind: WorkflowKind;
  stageKey: string;
  entry: StageHistoryEntry;
  docs?: StageDocs;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  // A snapshot is only usable when it carries the full order (lines). Older audit entries, written
  // before snapshots existed, hold just the event payload — treat those as no snapshot so the panel
  // falls back to the live documents below instead of crashing on missing fields.
  const snap = entry.snapshot && Array.isArray(entry.snapshot.lines) ? entry.snapshot : null;

  const when = new Intl.DateTimeFormat(i18n.language, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(entry.at));

  const isSales = kind === "sales";
  const partyType = isSales ? "customer" : "supplier";
  const partyCode = snap ? (isSales ? snap.customer_code : snap.supplier_code) ?? "" : "";
  const partyName = snap ? (isSales ? snap.customer_name : snap.supplier_name) ?? "" : "";
  const currency = snap?.currency;
  const outstanding = snap?.outstanding_minor ?? 0;

  // Stage → the document it produced. The invoice (sales) and bill (purchasing) stages both post a
  // GL journal; the deliver/receive stages move stock; a return posts the credit/debit note.
  const isInvoiceStage = stageKey === (isSales ? "invoice" : "bill");
  const isDeliveryStage = stageKey === (isSales ? "deliver" : "receive");
  const isReturnStage = stageKey === "returned";

  const invoiceNo = docs?.invoiceNumber ?? snap?.invoice_number ?? snap?.bill_number ?? null;
  const creditNo = docs?.creditNoteNumber ?? snap?.credit_note_number ?? snap?.debit_note_number ?? null;

  // The stock movements behind a delivery/receipt are keyed by the order number (their reference).
  const ref = docs?.orderNumber ?? snap?.number ?? "";
  const wantMovements = isDeliveryStage && !!ref;
  const { data: movements } = useAsync<Movement[]>(
    () => (wantMovements ? movementsForReference(ref) : Promise.resolve([])),
    [ref, wantMovements],
    wantMovements ? `movements:ref:${ref}` : undefined,
  );

  return (
    <div className="wf-snap card" role="group" aria-label={t(`workflow.${kind}.${stageKey}`)}>
      <div className="wf-snap__head">
        <div>
          <p className="wf-snap__stage">{t(`workflow.${kind}.${stageKey}`)}</p>
          <p className="wf-snap__meta">
            {entry.actor_name
              ? t("workflow.stage.byWhen", { who: entry.actor_name, when })
              : t("workflow.stage.when", { when })}
          </p>
        </div>
        <button type="button" className="wf-snap__close" onClick={onClose} aria-label={t("common.close")}>
          <NavIcon name="close" />
        </button>
      </div>

      {isInvoiceStage && invoiceNo && (
        <div className="wf-snap__docs">
          <span className="wf-snap__docs-title">{t(isSales ? "sales.detail.invoiceNo" : "purchasing.detail.billNo")}</span>
          <span className="latin"><EntityLink type="journal" value={invoiceNo} /></span>
        </div>
      )}

      {isReturnStage && creditNo && (
        <div className="wf-snap__docs">
          <span className="wf-snap__docs-title">{t(isSales ? "sales.detail.creditNoteNo" : "purchasing.detail.debitNoteNo")}</span>
          <span className="latin"><EntityLink type="journal" value={creditNo} /></span>
        </div>
      )}

      {isDeliveryStage && (
        <div className="wf-snap__table-wrap">
          <p className="wf-snap__docs-title">{t("workflow.snap.movements")}</p>
          {movements && movements.length > 0 ? (
            <table className="wf-snap__table">
              <thead>
                <tr>
                  <th>{t("sales.newOrder.item")}</th>
                  <th>{t("inventory.warehouse.code")}</th>
                  <th className="wf-snap__num">{t("inventory.onHand.quantity")}</th>
                  <th>{t("accounting.journals.number")}</th>
                </tr>
              </thead>
              <tbody>
                {movements.map((m) => (
                  <tr key={m.id}>
                    <td><EntityLink type="item" value={m.item_sku} /></td>
                    <td><EntityLink type="warehouse" value={m.warehouse_code} /></td>
                    <td className="wf-snap__num"><Bdi>{m.quantity}</Bdi></td>
                    <td className="latin">
                      {m.journal_number ? (
                        <EntityLink type="journal" value={m.journal_number} />
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="wf-snap__meta">{t("inventory.detail.noMovements")}</p>
          )}
        </div>
      )}

      {snap && (
        <>
          <dl className="wf-snap__facts">
            <div className="wf-snap__fact">
              <dt>{t("workflow.snap.status")}</dt>
              <dd>{t(`${kind}.status.${snap.status}`)}</dd>
            </div>
            <div className="wf-snap__fact">
              <dt>{t(isSales ? "party.customer" : "party.supplier")}</dt>
              <dd>
                <EntityLink type={partyType} value={partyCode}>
                  {partyName || partyCode}
                </EntityLink>
              </dd>
            </div>
            <div className="wf-snap__fact">
              <dt>{t("inventory.warehouse.code")}</dt>
              <dd>
                <EntityLink type="warehouse" value={snap.warehouse_code} />
              </dd>
            </div>
            <div className="wf-snap__fact">
              <dt>{t("workflow.snap.date")}</dt>
              <dd className="latin">{snap.order_date}</dd>
            </div>
          </dl>

          <div className="wf-snap__table-wrap">
            <table className="wf-snap__table">
              <thead>
                <tr>
                  <th>{t("sales.newOrder.item")}</th>
                  <th className="wf-snap__num">{t("inventory.onHand.quantity")}</th>
                  <th className="wf-snap__num">
                    {isSales ? t("sales.detail.delivered") : t("purchasing.detail.received")}
                  </th>
                  <th className="wf-snap__num">{t("sales.orders.total")}</th>
                </tr>
              </thead>
              <tbody>
                {snap.lines.map((l) => (
                  <tr key={l.line_no}>
                    <td>
                      <EntityLink type="item" value={l.item_sku} />
                      {l.description ? ` · ${l.description}` : ""}
                    </td>
                    <td className="wf-snap__num"><Bdi>{l.quantity}</Bdi></td>
                    <td className="wf-snap__num">
                      <Bdi>{isSales ? l.delivered_qty : l.received_qty}</Bdi>
                    </td>
                    <td className="wf-snap__num"><Bdi>{formatMinor(l.line_total_minor)}</Bdi></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="wf-snap__totals">
            <div className="wf-snap__total">
              <span>{t("sales.orders.total")}</span>
              <span><Bdi>{formatMinor(snap.subtotal_minor, currency)}</Bdi></span>
            </div>
            {snap.tax_minor > 0 && (
              <div className="wf-snap__total">
                <span>{t("sales.detail.vat")}</span>
                <span><Bdi>{formatMinor(snap.tax_minor, currency)}</Bdi></span>
              </div>
            )}
            <div className="wf-snap__total">
              <span>{t("sales.detail.outstanding")}</span>
              <span><Bdi>{formatMinor(outstanding, currency)}</Bdi></span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
