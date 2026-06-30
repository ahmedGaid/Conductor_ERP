import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  convertLead,
  createLead,
  listLeads,
  setLeadStatus,
  type Lead,
  type Opportunity,
} from "../../api/crm";
import { useAsync } from "../../hooks/useAsync";
import { Badge } from "../../components/Badge";
import { crmTone } from "../../lib/statusTone";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate, runOptimistic } from "../../lib/optimistic";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { RowActions } from "../../components/RowActions";
import { CrmNav } from "./CrmNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./crm.css";

const LEAD_STATUSES = ["new", "contacted", "qualified", "unqualified", "converted"] as const;
const LEAD_SOURCES = ["web", "referral", "call", "campaign", "other"] as const;

export function LeadsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(() => listLeads(), [], "crm:leads");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<Lead>[]>(
    () => [
      {
        key: "status",
        label: t("common.status"),
        type: "select",
        options: LEAD_STATUSES.map((s) => ({ value: s, label: t(`crm.leadStatus.${s}`) })),
        accessor: (l) => l.status,
      },
      { key: "name", label: t("crm.lead.name"), type: "text", accessor: (l) => l.name },
      {
        key: "source",
        label: t("crm.lead.source"),
        type: "select",
        options: LEAD_SOURCES.map((s) => ({ value: s, label: t(`crm.source.${s}`) })),
        accessor: (l) => l.source,
      },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((l) => matchesAllFilters(l, fields, filters)) : data),
    [data, fields, filters],
  );

  const statusTabs = useMemo(
    () => LEAD_STATUSES.map((s) => ({ value: s, label: t(`crm.leadStatus.${s}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((l) => l.status === tab)) : filtered),
    [filtered, tab],
  );

  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [email, setEmail] = useState("");
  const [source, setSource] = useState("web");

  // Optimistic create: show the new lead row instantly and clear the form for the next entry; the
  // server row (with its assigned code) replaces the placeholder on settle, or it rolls back + toasts.
  function onAdd(e: FormEvent) {
    e.preventDefault();
    const n = name.trim();
    if (!n) return;
    void optimisticCreate<Lead>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, code: "", name: n, company, email, source, status: "new" }) as Lead,
      request: () => createLead({ name: n, company, email, source }),
      toast,
      success: t("crm.toast.leadCreated"),
    });
    setName("");
    setCompany("");
    setEmail("");
  }

  // Optimistic row transition: patch the lead in place, reconcile with the server's lead, roll back
  // + toast on failure.
  function patchLead(id: string, apply: (l: Lead) => Lead, request: () => Promise<Lead>, success: string) {
    if (!data) return;
    void runOptimistic<Lead[], Lead>({
      current: data,
      mutate,
      optimistic: (rows) => rows.map((l) => (l.id === id ? apply(l) : l)),
      request,
      settle: (predicted, updated) => predicted.map((l) => (l.id === id ? updated : l)),
      toast,
      success,
    });
  }

  // Convert spawns a new opportunity (a different entity), so there's nothing on the lead row to
  // reconcile beyond the status flip — keep the predicted "converted" row; the opportunities list
  // is refreshed by apiFetch's write-invalidation.
  function convert(id: string) {
    if (!data) return;
    void runOptimistic<Lead[], Opportunity>({
      current: data,
      mutate,
      optimistic: (rows) => rows.map((l) => (l.id === id ? { ...l, status: "converted" } : l)),
      request: () => convertLead(id, { customer_code: "" }),
      toast,
      success: t("crm.toast.leadConverted"),
    });
  }

  return (
    <section className="crm-page">
      <CrmNav />

      <form className="card crm-page" onSubmit={onAdd}>
        <h2>{t("crm.lead.add")}</h2>
        <div className="crm-toolbar">
          <label className="crm-field">
            <span>{t("crm.lead.name")}</span>
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="crm-field">
            <span>{t("crm.lead.company")}</span>
            <input value={company} onChange={(e) => setCompany(e.target.value)} />
          </label>
          <label className="crm-field">
            <span>{t("crm.lead.email")}</span>
            <input className="latin" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="crm-field">
            <span>{t("crm.lead.source")}</span>
            <select value={source} onChange={(e) => setSource(e.target.value)}>
              {["web", "referral", "call", "campaign", "other"].map((s) => (
                <option key={s} value={s}>{t(`crm.source.${s}`)}</option>
              ))}
            </select>
          </label>
          <button type="submit" className="btn btn--primary">
            {t("crm.lead.add")}
          </button>
        </div>
      </form>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <EmptyState title={t("crm.lead.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="crm-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={statusTabs}
          accessor={(l) => l.status}
          value={tab}
          onChange={setTab}
          ariaLabel={t("common.status")}
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
                <th>{t("crm.lead.code")}</th>
                <th>{t("crm.lead.name")}</th>
                <th>{t("crm.lead.company")}</th>
                <th>{t("crm.lead.source")}</th>
                <th>{t("crm.opp.stage")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {visible.map((l: Lead) => (
                <tr key={l.id}>
                  <td className="latin">{l.code}</td>
                  <td>{l.name}</td>
                  <td>{l.company || "—"}</td>
                  <td className="muted">{t(`crm.source.${l.source}`)}</td>
                  <td>
                    <Badge tone={crmTone(l.status)}>{t(`crm.leadStatus.${l.status}`)}</Badge>
                  </td>
                  <td>
                    <RowActions className="crm-actions" label={t("common.actions")}>
                      {l.status === "new" && (
                        <button
                          className="btn btn--sm"
                          onClick={() => patchLead(l.id, (lead) => ({ ...lead, status: "qualified" }), () => setLeadStatus(l.id, "qualified"), t("crm.toast.leadQualified"))}
                        >
                          {t("crm.leadStatus.qualified")}
                        </button>
                      )}
                      {l.status !== "converted" && (
                        <button className="btn btn--sm btn--primary" onClick={() => convert(l.id)}>
                          {t("crm.lead.convert")}
                        </button>
                      )}
                    </RowActions>
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
