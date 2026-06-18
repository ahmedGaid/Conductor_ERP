import { useState, type FormEvent } from "react";
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
import { EmptyState } from "../../components/EmptyState";
import { CrmNav } from "./CrmNav";
import "./crm.css";

const PRIORITIES: TicketPriority[] = ["low", "medium", "high", "urgent"];

export function TicketsPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(() => listTickets(), [], "crm:tickets");

  const [subject, setSubject] = useState("");
  const [customer, setCustomer] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("medium");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!subject) {
      setFormError(t("crm.ticket.needSubject"));
      return;
    }
    setBusy(true);
    try {
      await createTicket({ subject, customer_code: customer, priority });
      setSubject("");
      setCustomer("");
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
      <h1>{t("nav.crm")}</h1>
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
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {t("crm.ticket.add")}
          </button>
        </div>
        {formError && <p className="error-text">{formError}</p>}
      </form>

      {data && data.length > 0 && (
        <div className="crm-toolbar">
          <button className="btn btn--sm" disabled={busy} onClick={() => act(() => runEscalations())}>
            {t("crm.ticket.runEscalations")}
          </button>
          <span className="muted" style={{ fontSize: "var(--font-size-sm)" }}>{t("crm.ticket.runEscalationsHint")}</span>
        </div>
      )}

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
        <EmptyState title={t("crm.ticket.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
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
              {data.map((tk: Ticket) => (
                <tr key={tk.id}>
                  <td className="latin">{tk.number}</td>
                  <td>{tk.subject}</td>
                  <td>
                    <span className={`crm-prio crm-prio--${tk.priority}`}>{t(`crm.priority.${tk.priority}`)}</span>
                  </td>
                  <td>
                    <span className={`crm-badge crm-badge--${tk.status}`}>{t(`crm.ticketStatus.${tk.status}`)}</span>
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
                    <div className="crm-actions">
                      {tk.status === "open" && (
                        <button className="btn btn--sm" disabled={busy} onClick={() => act(() => startTicket(tk.id))}>
                          {t("crm.ticket.start")}
                        </button>
                      )}
                      {tk.is_breached && !tk.is_escalated && (tk.status === "open" || tk.status === "in_progress") && (
                        <button className="btn btn--sm btn--danger" disabled={busy} onClick={() => act(() => escalateTicket(tk.id))}>
                          {t("crm.ticket.escalate")}
                        </button>
                      )}
                      {(tk.status === "open" || tk.status === "in_progress") && (
                        <button className="btn btn--sm btn--primary" disabled={busy} onClick={() => act(() => resolveTicket(tk.id))}>
                          {t("crm.ticket.resolve")}
                        </button>
                      )}
                      {tk.status === "resolved" && (
                        <button className="btn btn--sm" disabled={busy} onClick={() => act(() => closeTicket(tk.id))}>
                          {t("crm.ticket.close")}
                        </button>
                      )}
                    </div>
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
