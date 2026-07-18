import { useMemo, useRef, useState, type FormEvent } from "react";
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
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { StatusRing } from "../../components/StatusRing";
import { OwnerChip } from "../../components/OwnerChip";
import { crmTone } from "../../lib/statusTone";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate, runOptimistic } from "../../lib/optimistic";
import { useUndoableAction } from "../../lib/useUndoableAction";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { RowActions } from "../../components/RowActions";
import { CrmNav } from "./CrmNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import { useFormKeys } from "../../hooks/useFormKeys";
import { useSetHelpSignals } from "../../help/HelpSignalsContext";
import "./crm.css";

const LEAD_STATUSES = ["new", "contacted", "qualified", "unqualified", "converted"] as const;
const LEAD_SOURCES = ["web", "referral", "call", "campaign", "other"] as const;

export function LeadsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const undoable = useUndoableAction();
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
  const savedViews = useSavedViews({ listKey: "crm:leads", fields, filters, setFilters });
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

  // ⌘/Ctrl+Enter submits the add-lead form from any field (incl. the source select).
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

  // Publish the page's live facts for the Help drawer's Live tab.
  useSetHelpSignals({ leadCount: (data ?? []).length });

  // Multi-select for bulk qualify (mirrors the per-row "qualify" on a new lead).
  const selection = useRowSelection<Lead>({
    items: visible ?? [],
    getItemId: (l) => l.id,
  });
  const qualifiable = selection.selectedItems.filter((l) => l.status === "new");

  // Qualify many new leads in one optimistic pass, then clear the selection.
  function bulkQualify() {
    if (qualifiable.length === 0 || !data) return;
    const ids = new Set(qualifiable.map((l) => l.id));
    void runOptimistic<Lead[], Lead[]>({
      current: data,
      mutate,
      optimistic: (rows) => rows.map((l) => (ids.has(l.id) ? { ...l, status: "qualified" } : l)),
      request: () => Promise.all(qualifiable.map((l) => setLeadStatus(l.id, "qualified"))),
      settle: (rows, updated) => {
        const byId = new Map(updated.map((u) => [u.id, u]));
        return rows.map((l) => byId.get(l.id) ?? l);
      },
      toast,
      success: t(qualifiable.length === 1 ? "crm.toast.bulkLeadsQualifiedOne" : "crm.toast.bulkLeadsQualified", { count: qualifiable.length }),
    });
    selection.clear();
  }

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

  // Qualifying a lead is reversible (its inverse just restores the prior status), so it's an
  // undo-not-confirm action: flip the row instantly, then offer Undo instead of asking first.
  // `onUndone` restores the exact pre-action rows — it runs on an Undo click and if the call fails.
  function qualifyLead(l: Lead) {
    if (!data) return;
    const snapshot = data;
    const prev = l.status;
    mutate(snapshot.map((row) => (row.id === l.id ? { ...row, status: "qualified" } : row)));
    void undoable<Lead>({
      perform: () => setLeadStatus(l.id, "qualified"),
      undo: async () => {
        await setLeadStatus(l.id, prev);
      },
      message: t("crm.toast.leadQualified"),
      onUndone: () => mutate(snapshot),
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

  // j/k move a row highlight; Enter/o converts the highlighted lead (its primary action) — these
  // lists have no detail page, so the keyboard acts on the row in place. An already-converted lead
  // has no next step, so Enter is a no-op there. Highlight + scroll restore on return.
  const { active } = useListKeyboardNav<Lead>({
    items: visible ?? [],
    onOpen: (l) => {
      if (l.status !== "converted") convert(l.id);
    },
    persistKey: "crm:leads",
    getItemId: (l) => l.id,
  });

  // Add is a form (forms keep their controls) — no bar primary, just print + CSV.
  const csvColumns = useMemo<CsvColumn<Lead>[]>(
    () => [
      { header: t("crm.lead.code"), accessor: (l) => l.code },
      { header: t("crm.lead.name"), accessor: (l) => l.name },
      { header: t("crm.lead.company"), accessor: (l) => l.company || "" },
      { header: t("crm.lead.source"), accessor: (l) => t(`crm.source.${l.source}`) },
      { header: t("common.status"), accessor: (l) => t(`crm.leadStatus.${l.status}`) },
    ],
    [t],
  );
  useListPageActions({ rows: visible, columns: csvColumns, filename: "leads" });

  return (
    <section className="crm-page">
      <CrmNav />

      <form ref={formRef} className="card crm-page" onSubmit={onAdd}>
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
          <SavedViews api={savedViews} />
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
                <th>{t("crm.lead.code")}</th>
                <th>{t("crm.lead.name")}</th>
                <th>{t("crm.lead.company")}</th>
                <th>{t("crm.lead.source")}</th>
                <th>{t("common.owner")}</th>
                <th>{t("crm.opp.stage")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {visible.map((l: Lead, i) => (
                <tr
                  key={l.id}
                  data-kbd-active={i === active ? "true" : undefined}
                  data-selected={selection.isSelected(l.id) ? "true" : undefined}
                  aria-selected={selection.isSelected(l.id)}
                >
                  <SelectRowCell
                    className="crm-table__select"
                    checked={selection.isSelected(l.id)}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
                  <td className="latin">{l.code}</td>
                  <td>{l.name}</td>
                  <td>{l.company || "—"}</td>
                  <td className="muted">{t(`crm.source.${l.source}`)}</td>
                  <td>{l.owner ? <OwnerChip name={l.owner} /> : "—"}</td>
                  <td>
                    <StatusRing
                      docType="lead"
                      status={l.status}
                      tone={crmTone(l.status)}
                      label={t(`crm.leadStatus.${l.status}`)}
                    />
                  </td>
                  <td>
                    <RowActions className="crm-actions" label={t("common.actions")}>
                      {l.status === "new" && (
                        <button className="btn btn--sm" onClick={() => qualifyLead(l)}>
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

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        {qualifiable.length > 0 && (
          <button className="btn btn--sm" onClick={bulkQualify}>
            {t("crm.leadStatus.qualified")}
          </button>
        )}
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("leads-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
