import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  convertLead,
  createLead,
  listLeads,
  setLeadStatus,
  type Lead,
} from "../../api/crm";
import { useAsync } from "../../hooks/useAsync";
import { CrmNav } from "./CrmNav";
import "./crm.css";

export function LeadsPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(() => listLeads(), [], "crm:leads");

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
      <h1>{t("nav.crm")}</h1>
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
      {data && data.length === 0 && <p className="muted">{t("crm.lead.empty")}</p>}

      {data && data.length > 0 && (
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
              {data.map((l: Lead) => (
                <tr key={l.id}>
                  <td className="latin">{l.code}</td>
                  <td>{l.name}</td>
                  <td>{l.company || "—"}</td>
                  <td className="muted">{t(`crm.source.${l.source}`)}</td>
                  <td>
                    <span className={`crm-badge crm-badge--${l.status}`}>{t(`crm.leadStatus.${l.status}`)}</span>
                  </td>
                  <td>
                    <div className="crm-actions">
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
