import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { getCampaign, setCampaignStatus, type CampaignStatus } from "../../api/crm";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { CrmNav } from "./CrmNav";
import "./crm.css";

const NEXT: Record<CampaignStatus, CampaignStatus | null> = {
  draft: "active",
  active: "completed",
  completed: null,
};

export function CampaignDetailPage() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const { data: campaign, loading, error, reload } = useAsync(() => getCampaign(id), [id]);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function changeStatus(status: CampaignStatus) {
    setBusy(true);
    setActionError(null);
    try {
      await setCampaignStatus(id, status);
      reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const m = campaign?.metrics;
  const next = campaign ? NEXT[campaign.status] : null;

  return (
    <section className="crm-page">
      <h1>{t("nav.crm")}</h1>
      <CrmNav />
      <Link className="crm-link" to="/crm/campaigns">← {t("crm.campaign.backToList")}</Link>

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}

      {campaign && (
        <div className="card crm-detail">
          <div className="crm-detail-head">
            <h2><Bdi>{campaign.code}</Bdi> — {campaign.name}</h2>
            <div className="crm-toolbar">
              <span className={`crm-badge crm-badge--${campaign.status}`}>{t(`crm.campaign.statuses.${campaign.status}`)}</span>
              {next && (
                <button className="btn btn--sm btn--primary" disabled={busy} onClick={() => changeStatus(next)}>
                  {t(`crm.campaign.markActions.${next}`)}
                </button>
              )}
            </div>
          </div>
          {actionError && <p className="error-text">{actionError}</p>}

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
          <p className="muted" style={{ fontSize: "var(--font-size-sm)" }}>{t("crm.campaign.linkHint")}</p>
        </div>
      )}
    </section>
  );
}
