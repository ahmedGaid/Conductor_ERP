import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import {
  advanceStage,
  getOpportunity,
  loseOpportunity,
  winOpportunity,
  type Opportunity,
  type OppStage,
} from "../../api/crm";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { CrmNav } from "./CrmNav";
import "./crm.css";

const NEXT_STAGE: Partial<Record<OppStage, OppStage>> = {
  qualifying: "proposal",
  proposal: "negotiation",
};

export function OpportunityDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, mutate } = useAsync<Opportunity>(
    () => getOpportunity(id as string),
    [id],
    `crm:opportunity:${id}`,
  );

  // Optimistic: flip the stage instantly so the badge and action set update, then let the server's
  // returned opportunity reconcile derived values (weighted amount, spawned sales order). A failure
  // rolls the whole opportunity back and shows an error toast.
  function act(apply: (o: Opportunity) => Opportunity, request: () => Promise<Opportunity>, success: string) {
    if (!data) return;
    void runOptimistic<Opportunity, Opportunity>({
      current: data,
      mutate,
      optimistic: apply,
      request,
      settle: (_predicted, updated) => updated,
      toast,
      success,
    });
  }

  return (
    <section className="crm-page">
      <CrmNav />

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
          <div className="card crm-page">
            <div className="crm-page__head">
              <div>
                <h2 className="latin">{data.number}</h2>
                <p className="muted">
                  {data.name}
                  {data.customer_code ? ` · ${data.customer_code}` : ""}
                  {data.lead_code ? ` · ${data.lead_code}` : ""}
                </p>
              </div>
              <span className={`crm-badge crm-badge--${data.stage}`}>{t(`crm.stage.${data.stage}`)}</span>
            </div>

            <div className="crm-summary">
              <div className="crm-summary__item">
                <span className="crm-summary__label">{t("crm.opp.amount")}</span>
                <span className="crm-summary__value"><Bdi>{formatMinor(data.amount_minor, data.currency)}</Bdi></span>
              </div>
              <div className="crm-summary__item">
                <span className="crm-summary__label">{t("crm.opp.probability")}</span>
                <span className="crm-summary__value"><Bdi>{data.probability}%</Bdi></span>
              </div>
              <div className="crm-summary__item">
                <span className="crm-summary__label">{t("crm.opp.weighted")}</span>
                <span className="crm-summary__value"><Bdi>{formatMinor(data.weighted_minor, data.currency)}</Bdi></span>
              </div>
              {data.sales_order_number && (
                <div className="crm-summary__item">
                  <span className="crm-summary__label">{t("crm.opp.salesOrder")}</span>
                  <Link className="latin" to={`/sales/orders`}>{data.sales_order_number}</Link>
                </div>
              )}
            </div>

            {(data.stage === "qualifying" || data.stage === "proposal" || data.stage === "negotiation") && (
              <div className="crm-actions">
                {NEXT_STAGE[data.stage] && (
                  <button
                    className="btn"
                    onClick={() => {
                      const next = NEXT_STAGE[data.stage]!;
                      act((o) => ({ ...o, stage: next }), () => advanceStage(data.id, next), t("crm.toast.stageAdvanced", { stage: t(`crm.stage.${next}`) }));
                    }}
                  >
                    {t("crm.detail.advanceTo", { stage: t(`crm.stage.${NEXT_STAGE[data.stage]}`) })}
                  </button>
                )}
                <button
                  className="btn btn--primary"
                  onClick={() => act((o) => ({ ...o, stage: "won" }), () => winOpportunity(data.id, data.lines.length > 0), t("crm.toast.oppWon"))}
                >
                  {t("crm.detail.win")}
                </button>
                <button
                  className="btn btn--danger"
                  onClick={() => act((o) => ({ ...o, stage: "lost" }), () => loseOpportunity(data.id), t("crm.toast.oppLost"))}
                >
                  {t("crm.detail.lose")}
                </button>
              </div>
            )}
          </div>

          {data.lines.length > 0 && (
            <div className="card crm-table-wrap">
              <table className="crm-table">
                <thead>
                  <tr>
                    <th>{t("sales.newOrder.item")}</th>
                    <th className="crm-table__num">{t("inventory.onHand.quantity")}</th>
                    <th className="crm-table__num">{t("sales.newOrder.unitPrice")}</th>
                    <th className="crm-table__num">{t("sales.orders.total")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.lines.map((l) => (
                    <tr key={l.line_no}>
                      <td><Bdi>{l.item_sku}</Bdi>{l.description ? ` · ${l.description}` : ""}</td>
                      <td className="crm-table__num"><Bdi>{l.quantity}</Bdi></td>
                      <td className="crm-table__num"><Bdi>{formatMinor(l.unit_price_minor)}</Bdi></td>
                      <td className="crm-table__num"><Bdi>{formatMinor(l.line_total_minor)}</Bdi></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
