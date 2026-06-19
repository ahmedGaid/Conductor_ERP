import { useState } from "react";
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
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload } = useAsync<Opportunity>(
    () => getOpportunity(id as string),
    [id],
  );
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function run(fn: () => Promise<Opportunity>) {
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
                  <button className="btn" disabled={busy} onClick={() => run(() => advanceStage(data.id, NEXT_STAGE[data.stage]!))}>
                    {t("crm.detail.advanceTo", { stage: t(`crm.stage.${NEXT_STAGE[data.stage]}`) })}
                  </button>
                )}
                <button className="btn btn--primary" disabled={busy} onClick={() => run(() => winOpportunity(data.id, data.lines.length > 0))}>
                  {t("crm.detail.win")}
                </button>
                <button className="btn btn--danger" disabled={busy} onClick={() => run(() => loseOpportunity(data.id))}>
                  {t("crm.detail.lose")}
                </button>
              </div>
            )}
            {actionError && <p className="error-text">{actionError}</p>}
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
