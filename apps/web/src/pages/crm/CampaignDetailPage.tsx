import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { BackLink } from "../../components/BackLink";

import { getCampaign, setCampaignStatus, type Campaign, type CampaignStatus } from "../../api/crm";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { useSetPageActions } from "../../app/PageActionsContext";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { DocumentPrimaryButton } from "../../components/DocumentHeader";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { copyShareLink, printDocument } from "../../lib/documentActions";
import { ErrorState } from "../../components/ErrorState";
import { useUndoableAction } from "../../lib/useUndoableAction";
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
  const { id = "" } = useParams();
  const undoable = useUndoableAction();
  const { data: campaign, loading, error, reload, mutate } = useAsync<Campaign>(
    () => getCampaign(id),
    [id],
    `crm:campaign:${id}`,
  );

  // Status steps are a field flip with no side effect (the backend allows moving either
  // direction), so it's undo-not-confirm: flip instantly, offer Undo instead of asking first.
  function changeStatus(status: CampaignStatus) {
    if (!campaign) return;
    const prev = campaign.status;
    mutate({ ...campaign, status });
    void undoable<Campaign>({
      perform: () => setCampaignStatus(id, status),
      undo: async () => {
        await setCampaignStatus(id, prev);
      },
      message: status === "active" ? t("crm.toast.campaignActivated") : t("crm.toast.campaignCompleted"),
      onUndone: () => mutate(campaign),
    });
  }

  const m = campaign?.metrics;
  const next = campaign ? NEXT[campaign.status] : null;
  const toast = useToast();

  useSetDocumentCrumb(campaign?.code);

  // Bar primary = the campaign's one next status step (activate → complete), same gating as the old
  // in-head button.
  const barPrimary = useMemo(() => {
    if (!campaign || !next) return undefined;
    return (
      <DocumentPrimaryButton
        action={{ label: t(`crm.campaign.markActions.${next}`), onClick: () => changeStatus(next) }}
      />
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaign, next, t]);
  const barMenu = useMemo<DocMenuItem[]>(() => {
    if (!campaign) return [];
    return [
      { key: "print", label: t("document.print"), icon: "print", onClick: () => printDocument(campaign.code) },
      { key: "pdf", label: t("document.exportPdf"), icon: "download", onClick: () => printDocument(campaign.code) },
      {
        key: "share",
        label: t("document.share"),
        icon: "share",
        onClick: () =>
          void copyShareLink(`/crm/campaigns/${id}`).then((ok) =>
            toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
          ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaign, t]);
  useSetPageActions({ primary: barPrimary, menuItems: barMenu });

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
