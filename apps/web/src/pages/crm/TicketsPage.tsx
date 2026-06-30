import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  createTicket,
  escalateTicket,
  listTickets,
  resolveTicket,
  runEscalations,
  startTicket,
  closeTicket,
  type Ticket,
  type TicketPriority,
} from "../../api/crm";
import { useAsync } from "../../hooks/useAsync";
import { Badge } from "../../components/Badge";
import { crmTone, crmPriorityTone } from "../../lib/statusTone";
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

const PRIORITIES: TicketPriority[] = ["low", "medium", "high", "urgent"];
const TICKET_STATUSES = ["open", "in_progress", "resolved", "closed"] as const;

export function TicketsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(() => listTickets(), [], "crm:tickets");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<Ticket>[]>(
    () => [
      {
        key: "status",
        label: t("common.status"),
        type: "select",
        options: TICKET_STATUSES.map((s) => ({ value: s, label: t(`crm.ticketStatus.${s}`) })),
        accessor: (tk) => tk.status,
      },
      {
        key: "priority",
        label: t("crm.ticket.priority"),
        type: "select",
        options: PRIORITIES.map((p) => ({ value: p, label: t(`crm.priority.${p}`) })),
        accessor: (tk) => tk.priority,
      },
      { key: "subject", label: t("crm.ticket.subject"), type: "text", accessor: (tk) => tk.subject },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((tk) => matchesAllFilters(tk, fields, filters)) : data),
    [data, fields, filters],
  );

  const statusTabs = useMemo(
    () => TICKET_STATUSES.map((s) => ({ value: s, label: t(`crm.ticketStatus.${s}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((tk) => tk.status === tab)) : filtered),
    [filtered, tab],
  );

  const [subject, setSubject] = useState("");
  const [customer, setCustomer] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("medium");

  // Optimistic create: open the new ticket row instantly and clear the form for the next entry; the
  // server row (with its number + SLA flags) replaces the placeholder on settle, or it rolls back + toasts.
  function onAdd(e: FormEvent) {
    e.preventDefault();
    const s = subject.trim();
    if (!s) return;
    void optimisticCreate<Ticket>({
      current: data ?? [],
      mutate,
      placeholder: (id) =>
        ({ id, number: "", subject: s, customer_code: customer, priority, status: "open", is_breached: false, is_escalated: false }) as Ticket,
      request: () => createTicket({ subject: s, customer_code: customer, priority }),
      toast,
      success: t("crm.toast.ticketCreated"),
    });
    setSubject("");
    setCustomer("");
  }

  // Optimistic per-row transition: patch the ticket in place, reconcile with the server's ticket
  // (it recomputes escalation/SLA flags), roll back + toast on failure.
  function patchTicket(id: string, apply: (tk: Ticket) => Ticket, request: () => Promise<Ticket>, success: string) {
    if (!data) return;
    void runOptimistic<Ticket[], Ticket>({
      current: data,
      mutate,
      optimistic: (rows) => rows.map((tk) => (tk.id === id ? apply(tk) : tk)),
      request,
      settle: (predicted, updated) => predicted.map((tk) => (tk.id === id ? updated : tk)),
      toast,
      success,
    });
  }

  // Escalation sweep touches an unknown set of tickets server-side, so it can't be predicted; run
  // it, report how many were escalated, and refresh the list.
  async function onRunEscalations() {
    try {
      const res = await runEscalations();
      reload();
      toast.show(t("crm.toast.escalationsRun", { count: res.count }), "success");
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    }
  }

  return (
    <section className="crm-page">
      <CrmNav />

      <form className="card crm-page" onSubmit={onAdd}>
        <h2>{t("crm.ticket.add")}</h2>
        <div className="crm-toolbar">
          <label className="crm-field">
            <span>{t("crm.ticket.subject")}</span>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} />
          </label>
          <label className="crm-field">
            <span>{t("crm.ticket.customer")}</span>
            <input className="latin" value={customer} onChange={(e) => setCustomer(e.target.value)} />
          </label>
          <label className="crm-field">
            <span>{t("crm.ticket.priority")}</span>
            <select value={priority} onChange={(e) => setPriority(e.target.value as TicketPriority)}>
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>{t(`crm.priority.${p}`)}</option>
              ))}
            </select>
          </label>
          <button type="submit" className="btn btn--primary">
            {t("crm.ticket.add")}
          </button>
        </div>
      </form>

      {data && data.length > 0 && (
        <div className="crm-toolbar">
          <button className="btn btn--sm" onClick={onRunEscalations}>
            {t("crm.ticket.runEscalations")}
          </button>
          <span className="muted" style={{ fontSize: "var(--font-size-sm)" }}>{t("crm.ticket.runEscalationsHint")}</span>
        </div>
      )}

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <EmptyState title={t("crm.ticket.empty")} hint={t("common.emptyHint")} />
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
          accessor={(tk) => tk.status}
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
                <th>{t("crm.ticket.number")}</th>
                <th>{t("crm.ticket.subject")}</th>
                <th>{t("crm.ticket.priority")}</th>
                <th>{t("crm.opp.stage")}</th>
                <th>{t("crm.ticket.sla")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {visible.map((tk: Ticket) => (
                <tr key={tk.id}>
                  <td className="latin">{tk.number}</td>
                  <td>{tk.subject}</td>
                  <td>
                    <Badge tone={crmPriorityTone(tk.priority)}>{t(`crm.priority.${tk.priority}`)}</Badge>
                  </td>
                  <td>
                    <Badge tone={crmTone(tk.status)}>{t(`crm.ticketStatus.${tk.status}`)}</Badge>
                  </td>
                  <td>
                    {tk.is_breached ? (
                      <span className="crm-breach">{t("crm.ticket.breached")}</span>
                    ) : (
                      <span className="crm-ontime">{t("crm.ticket.onTime")}</span>
                    )}
                    {tk.is_escalated && <span className="crm-escalated">↑ {t("crm.ticket.escalated")}</span>}
                  </td>
                  <td>
                    <RowActions className="crm-actions" label={t("common.actions")}>
                      {tk.status === "open" && (
                        <button
                          className="btn btn--sm"
                          onClick={() => patchTicket(tk.id, (t0) => ({ ...t0, status: "in_progress" }), () => startTicket(tk.id), t("crm.toast.ticketStarted"))}
                        >
                          {t("crm.ticket.start")}
                        </button>
                      )}
                      {tk.is_breached && !tk.is_escalated && (tk.status === "open" || tk.status === "in_progress") && (
                        <button
                          className="btn btn--sm btn--danger"
                          onClick={() => patchTicket(tk.id, (t0) => ({ ...t0, is_escalated: true }), () => escalateTicket(tk.id), t("crm.toast.ticketEscalated"))}
                        >
                          {t("crm.ticket.escalate")}
                        </button>
                      )}
                      {(tk.status === "open" || tk.status === "in_progress") && (
                        <button
                          className="btn btn--sm btn--primary"
                          onClick={() => patchTicket(tk.id, (t0) => ({ ...t0, status: "resolved" }), () => resolveTicket(tk.id), t("crm.toast.ticketResolved"))}
                        >
                          {t("crm.ticket.resolve")}
                        </button>
                      )}
                      {tk.status === "resolved" && (
                        <button
                          className="btn btn--sm"
                          onClick={() => patchTicket(tk.id, (t0) => ({ ...t0, status: "closed" }), () => closeTicket(tk.id), t("crm.toast.ticketClosed"))}
                        >
                          {t("crm.ticket.close")}
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
