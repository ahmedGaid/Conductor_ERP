import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import {
  advanceStage,
  getOpportunity,
  loseOpportunity,
  updateOpportunity,
  winOpportunity,
  type Opportunity,
  type OppStage,
} from "../../api/crm";
import { useAsync } from "../../hooks/useAsync";
import { useRecentEntity } from "../../hooks/useRecentEntity";
import { usePaletteActions, type PaletteAction } from "../../app/PaletteActionsContext";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { InlineEdit } from "../../components/InlineEdit";
import { CrmNav } from "./CrmNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./crm.css";

const NEXT_STAGE: Partial<Record<OppStage, OppStage>> = {
  qualifying: "proposal",
  proposal: "negotiation",
};

export function OpportunityDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload, mutate } = useAsync<Opportunity>(
    () => getOpportunity(id as string),
    [id],
    `crm:opportunity:${id}`,
  );
  useRecentEntity(data?.number);

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

  // Inline edit of the opportunity's title: same optimistic flow, confirmed with a "Saved" toast
  // once it lands (a deliberate text edit, unlike the freely-clicked stage actions). Awaited so the
  // field holds its saving state until the round-trip settles.
  function saveField(changes: { name?: string; notes?: string }) {
    if (!data) return Promise.resolve();
    return runOptimistic<Opportunity, Opportunity>({
      current: data,
      mutate,
      optimistic: (o) => ({ ...o, ...changes }),
      request: () => updateOpportunity(data.id, changes),
      settle: (_predicted, updated) => updated,
      toast,
      success: t("common.saved"),
    });
  }

  // Stage actions mirrored into the ⌘K "This page" group, gated by stage exactly as the buttons
  // are (advance / win / lose only while the deal is open).
  const pageActions: PaletteAction[] = [];
  if (data && (data.stage === "qualifying" || data.stage === "proposal" || data.stage === "negotiation")) {
    const next = NEXT_STAGE[data.stage];
    if (next) {
      pageActions.push({ id: "advance", label: t("crm.detail.advanceTo", { stage: t(`crm.stage.${next}`) }),
        run: () => act((o) => ({ ...o, stage: next }), () => advanceStage(data.id, next), t("crm.toast.stageAdvanced", { stage: t(`crm.stage.${next}`) })) });
    }
    pageActions.push({ id: "win", label: t("crm.detail.win"),
      run: () => act((o) => ({ ...o, stage: "won" }), () => winOpportunity(data.id, data.lines.length > 0), t("crm.toast.oppWon")) });
    pageActions.push({ id: "lose", label: t("crm.detail.lose"),
      run: () => act((o) => ({ ...o, stage: "lost" }), () => loseOpportunity(data.id), t("crm.toast.oppLost")) });
  }
  usePaletteActions("opportunity-detail", pageActions);

  return (
    <section className="crm-page">
      <CrmNav />

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <>
          <div className="card crm-page">
            <div className="crm-page__head">
              <div className="crm-page__id">
                <h2 className="latin">{data.number}</h2>
                <div className="crm-page__name">
                  <InlineEdit
                    value={data.name}
                    label={t("crm.opp.name")}
                    placeholder={t("crm.detail.namePlaceholder")}
                    onSave={(v) => saveField({ name: v })}
                  />
                </div>
                {(data.customer_code || data.lead_code) && (
                  <p className="muted">
                    {data.customer_code}
                    {data.customer_code && data.lead_code ? " · " : ""}
                    {data.lead_code}
                  </p>
                )}
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

            <div className="crm-page__notes">
              <span className="crm-summary__label">{t("crm.opp.notes")}</span>
              <InlineEdit
                value={data.notes}
                label={t("crm.opp.notes")}
                placeholder={t("crm.detail.notesPlaceholder")}
                onSave={(v) => saveField({ notes: v })}
              />
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
