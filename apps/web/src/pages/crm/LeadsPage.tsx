import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  convertLead,
  createLead,
  listLeads,
  setLeadStatus,
  type Lead,
} from "../../api/crm";
import { useAsync } from "../../hooks/useAsync";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { RowActions } from "../../components/RowActions";
import { CrmNav } from "./CrmNav";
import "./crm.css";

const LEAD_STATUSES = ["new", "contacted", "qualified", "unqualified", "converted"] as const;
const LEAD_SOURCES = ["web", "referral", "call", "campaign", "other"] as const;

export function LeadsPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(() => listLeads(), [], "crm:leads");
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
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!name) {
      setFormError(t("crm.lead.needName"));
      return;
    }
    setBusy(true);
    try {
      await createLead({ name, company, email, source });
      setName("");
      setCompany("");
      setEmail("");
      reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setFormError(null);
    try {
      await fn();
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
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {t("crm.lead.add")}
          </button>
        </div>
        {formError && <p className="error-text">{formError}</p>}
      </form>

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
                    <span className={`crm-badge crm-badge--${l.status}`}>{t(`crm.leadStatus.${l.status}`)}</span>
                  </td>
                  <td>
                    <RowActions className="crm-actions" label={t("common.actions")}>
                      {l.status === "new" && (
                        <button className="btn btn--sm" disabled={busy} onClick={() => act(() => setLeadStatus(l.id, "qualified"))}>
                          {t("crm.leadStatus.qualified")}
                        </button>
                      )}
                      {l.status !== "converted" && (
                        <button className="btn btn--sm btn--primary" disabled={busy} onClick={() => act(() => convertLead(l.id, { customer_code: "" }))}>
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
