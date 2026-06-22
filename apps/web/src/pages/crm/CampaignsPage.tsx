import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { createCampaign, listCampaigns, type CampaignChannel } from "../../api/crm";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor, parseToMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { CrmNav } from "./CrmNav";
import "./crm.css";

const CHANNELS: CampaignChannel[] = ["email", "web", "call", "event", "social", "other"];
type Campaign = Awaited<ReturnType<typeof listCampaigns>>[number];

export function CampaignsPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listCampaigns, [], "crm:campaigns");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<Campaign>[]>(
    () => [
      { key: "code", label: t("crm.campaign.code"), type: "text", accessor: (c) => c.code },
      { key: "name", label: t("crm.campaign.name"), type: "text", accessor: (c) => c.name },
      {
        key: "channel",
        label: t("crm.campaign.channel"),
        type: "select",
        options: CHANNELS.map((c) => ({ value: c, label: t(`crm.campaign.channels.${c}`) })),
        accessor: (c) => c.channel,
      },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((c) => matchesAllFilters(c, fields, filters)) : data),
    [data, fields, filters],
  );

  const channelTabs = useMemo(
    () => CHANNELS.map((c) => ({ value: c, label: t(`crm.campaign.channels.${c}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((c) => c.channel === tab)) : filtered),
    [filtered, tab],
  );

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [channel, setChannel] = useState<CampaignChannel>("email");
  const [cost, setCost] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const costMinor = parseToMinor(cost || "0") ?? 0;
    if (!code || !name) {
      setFormError(t("crm.campaign.invalidInput"));
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      await createCampaign({ code, name, channel, cost_minor: costMinor });
      setCode("");
      setName("");
      setCost("");
      reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="crm-page">
      <CrmNav />

      <form className="card crm-toolbar" onSubmit={onSubmit}>
        <label className="crm-field">
          <span>{t("crm.campaign.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="crm-field" style={{ flex: 1 }}>
          <span>{t("crm.campaign.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="crm-field">
          <span>{t("crm.campaign.channel")}</span>
          <select value={channel} onChange={(e) => setChannel(e.target.value as CampaignChannel)}>
            {CHANNELS.map((c) => (
              <option key={c} value={c}>{t(`crm.campaign.channels.${c}`)}</option>
            ))}
          </select>
        </label>
        <label className="crm-field">
          <span>{t("crm.campaign.cost")}</span>
          <input className="latin" inputMode="decimal" value={cost} onChange={(e) => setCost(e.target.value)} placeholder="0.00" />
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>{t("crm.campaign.add")}</button>
      </form>
      {formError && <p className="error-text">{formError}</p>}

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}

      {data && data.length === 0 && (
        <EmptyState title={t("crm.campaign.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="crm-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={channelTabs}
          accessor={(c) => c.channel}
          value={tab}
          onChange={setTab}
          ariaLabel={t("crm.campaign.channel")}
        />
      )}
      {data && data.length > 0 && visible && visible.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {visible && visible.length > 0 && (
        <div className="card crm-table-wrap">
          <table className="crm-table">
            <thead>
              <tr>
                <th>{t("crm.campaign.code")}</th>
                <th>{t("crm.campaign.name")}</th>
                <th>{t("crm.campaign.channel")}</th>
                <th className="crm-num">{t("crm.campaign.cost")}</th>
                <th className="crm-num">{t("crm.campaign.wonValue")}</th>
                <th className="crm-num">{t("crm.campaign.roi")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link className="crm-link" to={`/crm/campaigns/${c.id}`}><Bdi>{c.code}</Bdi></Link>
                  </td>
                  <td>{c.name}</td>
                  <td>{t(`crm.campaign.channels.${c.channel}`)}</td>
                  <td className="crm-num"><Bdi>{formatMinor(c.cost_minor)}</Bdi></td>
                  <td className="crm-num"><Bdi>{formatMinor(c.metrics?.won_value_minor ?? 0)}</Bdi></td>
                  <td className={`crm-num ${(c.metrics?.roi_minor ?? 0) >= 0 ? "crm-ontime" : "crm-breach"}`}>
                    <Bdi>{formatMinor(c.metrics?.roi_minor ?? 0)}</Bdi>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
