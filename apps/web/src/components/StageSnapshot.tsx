import { useTranslation } from "react-i18next";

import type { StageHistoryEntry, WorkflowKind } from "../lib/workflow";
import { formatMinor } from "../lib/money";
import { Bdi } from "./Bdi";
import { EntityLink } from "./EntityLink";
import { NavIcon } from "../app/icons";
import "./stageSnapshot.css";

/**
 * StageSnapshot — the panel opened when a workflow tracker stage is clicked. Shows who reached the
 * stage and when, then the order exactly as it was at that point (the audit-trail snapshot): party,
 * warehouse, lines and totals. Read-only; monochrome chrome with the module accent only on links.
 */
export function StageSnapshot({
  kind,
  stageKey,
  entry,
  onClose,
}: {
  kind: WorkflowKind;
  stageKey: string;
  entry: StageHistoryEntry;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const snap = entry.snapshot;

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
