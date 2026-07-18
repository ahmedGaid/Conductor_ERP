import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { createCampaign, getCampaign, listCampaigns, type CampaignChannel } from "../../api/crm";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { useFormKeys } from "../../hooks/useFormKeys";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { prefetch } from "../../lib/prefetch";
import { formatMinor, parseToMinor } from "../../lib/money";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { CrmNav } from "./CrmNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./crm.css";

const CHANNELS: CampaignChannel[] = ["email", "web", "call", "event", "social", "other"];
type Campaign = Awaited<ReturnType<typeof listCampaigns>>[number];

export function CampaignsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(listCampaigns, [], "crm:campaigns");
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
  const savedViews = useSavedViews({ listKey: "crm:campaigns", fields, filters, setFilters });
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

  // j/k move a row highlight, Enter/o opens it on the detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<Campaign>({
    items: visible ?? [],
    onOpen: (c) => navigate(`/crm/campaigns/${c.id}`),
    persistKey: "crm:campaigns",
    getItemId: (c) => c.id,
  });

  // Add is a form (forms keep their controls) — no bar primary, just print + CSV.
  const csvColumns = useMemo<CsvColumn<Campaign>[]>(
    () => [
      { header: t("crm.campaign.code"), accessor: (c) => c.code },
      { header: t("crm.campaign.name"), accessor: (c) => c.name },
      { header: t("crm.campaign.channel"), accessor: (c) => t(`crm.campaign.channels.${c.channel}`) },
      { header: t("crm.campaign.cost"), accessor: (c) => formatMinor(c.cost_minor) },
      { header: t("crm.campaign.wonValue"), accessor: (c) => formatMinor(c.metrics?.won_value_minor ?? 0) },
      { header: t("crm.campaign.roi"), accessor: (c) => formatMinor(c.metrics?.roi_minor ?? 0) },
    ],
    [t],
  );
  useListPageActions({ rows: visible, columns: csvColumns, filename: "campaigns" });

  // Multi-select for bulk CSV export (no other bulk verb applies to campaigns).
  const selection = useRowSelection<Campaign>({
    items: visible ?? [],
    getItemId: (c) => c.id,
    activeIndex: active,
  });

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [channel, setChannel] = useState<CampaignChannel>("email");
  const [cost, setCost] = useState("");

  // ⌘/Ctrl+Enter submits the add form from any field (incl. the channel select).
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

  // Optimistic create: show the new campaign instantly and clear the form for the next entry. The row's
  // metrics columns are optional-chained, so an unmetered placeholder reads as zeros until the server
  // row settles in (or it rolls back + toasts on failure).
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const c = code.trim();
    const n = name.trim();
    if (!c || !n) return;
    const costMinor = parseToMinor(cost || "0") ?? 0;
    void optimisticCreate<Campaign>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, code: c, name: n, channel, cost_minor: costMinor }) as Campaign,
      request: () => createCampaign({ code: c, name: n, channel, cost_minor: costMinor }),
      toast,
      success: t("crm.toast.campaignCreated"),
    });
    setCode("");
    setName("");
    setCost("");
  }

  return (
    <section className="crm-page">
      <CrmNav />

      <form ref={formRef} className="card crm-toolbar" onSubmit={onSubmit}>
        <label className="crm-field">
          <span>{t("crm.campaign.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="crm-field grow">
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
        <button className="btn btn--primary" type="submit">{t("crm.campaign.add")}</button>
      </form>

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("crm.campaign.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="crm-filters">
          <SavedViews api={savedViews} />
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
        <EmptyState
          title={t("filter.noMatch")}
          hint={t("filter.noMatchHint")}
          action={{ label: t("filter.clearAll"), onClick: () => setFilters([]) }}
        />
      )}

      {visible && visible.length > 0 && (
        <div className="card crm-table-wrap">
          <table className="crm-table">
            <thead>
              <tr>
                <SelectAllCell
                  className="crm-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("crm.campaign.code")}</th>
                <th>{t("crm.campaign.name")}</th>
                <th>{t("crm.campaign.channel")}</th>
                <th className="crm-table__num">{t("crm.campaign.cost")}</th>
                <th className="crm-table__num">{t("crm.campaign.wonValue")}</th>
                <th className="crm-table__num">{t("crm.campaign.roi")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((c, i) => (
                <tr
                  key={c.id}
                  data-kbd-active={i === active ? "true" : undefined}
                  data-selected={selection.isSelected(c.id) ? "true" : undefined}
                  aria-selected={selection.isSelected(c.id) || i === active}
                >
                  <SelectRowCell
                    className="crm-table__select"
                    checked={selection.isSelected(c.id)}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
                  <td>
                    <Link
                      className="crm-link"
                      to={`/crm/campaigns/${c.id}`}
                      onMouseEnter={() => prefetch(`crm:campaign:${c.id}`, () => getCampaign(c.id))}
                      onFocus={() => prefetch(`crm:campaign:${c.id}`, () => getCampaign(c.id))}
                    >
                      <Bdi>{c.code}</Bdi>
                    </Link>
                  </td>
                  <td>{c.name}</td>
                  <td>{t(`crm.campaign.channels.${c.channel}`)}</td>
                  <td className="crm-table__num"><Bdi>{formatMinor(c.cost_minor)}</Bdi></td>
                  <td className="crm-table__num"><Bdi>{formatMinor(c.metrics?.won_value_minor ?? 0)}</Bdi></td>
                  <td className={`crm-table__num ${(c.metrics?.roi_minor ?? 0) >= 0 ? "crm-ontime" : "crm-breach"}`}>
                    <Bdi>{formatMinor(c.metrics?.roi_minor ?? 0)}</Bdi>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("campaigns-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
