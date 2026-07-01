import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { BackLink } from "../../components/BackLink";

import { getCampaign, setCampaignStatus, type Campaign, type CampaignStatus } from "../../api/crm";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { Badge } from "../../components/Badge";
import { crmTone } from "../../lib/statusTone";
import { CrmNav } from "./CrmNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./crm.css";

const NEXT: Record<CampaignStatus, CampaignStatus | null> = {
  draft: "active",
  active: "completed",
  completed: null,
};

export function CampaignDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { id = "" } = useParams();
  const { data: campaign, loading, error, reload, mutate } = useAsync<Campaign>(
    () => getCampaign(id),
    [id],
    `crm:campaign:${id}`,
  );

  // Optimistic status step: flip instantly, reconcile with the server's campaign (metrics may
  // change), roll back + toast on failure.
  function changeStatus(status: CampaignStatus) {
    if (!campaign) return;
    void runOptimistic<Campaign, Campaign>({
      current: campaign,
      mutate,
      optimistic: (c) => ({ ...c, status }),
      request: () => setCampaignStatus(id, status),
      settle: (_predicted, updated) => updated,
      toast,
      success: status === "active" ? t("crm.toast.campaignActivated") : t("crm.toast.campaignCompleted"),
    });
  }

  const m = campaign?.metrics;
  const next = campaign ? NEXT[campaign.status] : null;

  return (
    <section className="crm-page">
      <CrmNav />
      <BackLink to="/crm/campaigns">{t("crm.campaign.backToList")}</BackLink>

      {loading && (
        <ListSkeleton rows={1} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {campaign && (
        <div className="card crm-detail">
          <div className="crm-detail-head">
            <h2><Bdi>{campaign.code}</Bdi> — {campaign.name}</h2>
            <div className="crm-toolbar">
              <Badge tone={crmTone(campaign.status)}>{t(`crm.campaign.statuses.${campaign.status}`)}</Badge>
              {next && (
                <button className="btn btn--sm btn--primary" onClick={() => changeStatus(next)}>
                  {t(`crm.campaign.markActions.${next}`)}
                </button>
              )}
            </div>
          </div>

          {m && (
            <dl className="crm-metrics">
              <div><dt>{t("crm.campaign.leads")}</dt><dd><Bdi>{m.lead_count}</Bdi></dd></div>
              <div><dt>{t("crm.campaign.opportunities")}</dt><dd><Bdi>{m.opportunity_count}</Bdi></dd></div>
              <div><dt>{t("crm.campaign.won")}</dt><dd><Bdi>{m.won_count}</Bdi></dd></div>
              <div><dt>{t("crm.campaign.openPipeline")}</dt><dd><Bdi>{formatMinor(m.open_pipeline_minor)}</Bdi></dd></div>
              <div><dt>{t("crm.campaign.cost")}</dt><dd><Bdi>{formatMinor(campaign.cost_minor)}</Bdi></dd></div>
              <div><dt>{t("crm.campaign.wonValue")}</dt><dd><Bdi>{formatMinor(m.won_value_minor)}</Bdi></dd></div>
              <div>
                <dt>{t("crm.campaign.roi")}</dt>
                <dd className={m.is_profitable ? "crm-ontime" : "crm-breach"}><Bdi>{formatMinor(m.roi_minor)}</Bdi></dd>
              </div>
            </dl>
          )}
          <p className="hint">{t("crm.campaign.linkHint")}</p>
        </div>
      )}
    </section>
  );
}
