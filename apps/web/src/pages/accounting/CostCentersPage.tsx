import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createCostCenter, listCostCenters } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

export function CostCentersPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listCostCenters, [], "accounting:cost-centers");

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      await createCostCenter({ code, name });
      setCode("");
      setName("");
      reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="acct-page">
      <h1>{t("nav.accounting")}</h1>
      <AccountingNav />

      <form className="card acct-toolbar" onSubmit={onSubmit}>
        <label className="acct-field">
          <span>{t("accounting.costCenters.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="acct-field" style={{ flex: 1 }}>
          <span>{t("accounting.costCenters.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {t("accounting.costCenters.add")}
        </button>
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
        <EmptyState title={t("accounting.costCenters.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.costCenters.code")}</th>
                <th>{t("accounting.costCenters.name")}</th>
                <th>{t("accounting.costCenters.active")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((cc) => (
                <tr key={cc.id}>
                  <td><Bdi>{cc.code}</Bdi></td>
                  <td>{cc.name}</td>
                  <td>{cc.is_active ? t("common.yes") : t("common.no")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
