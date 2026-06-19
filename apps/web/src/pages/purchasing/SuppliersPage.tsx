import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createSupplier, listSuppliers } from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

export function SuppliersPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listSuppliers, [], "purchasing:suppliers");

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      await createSupplier({ code, name });
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
    <section className="pur-page">
      <h1>{t("nav.purchasing")}</h1>
      <PurchasingNav />

      <form className="card pur-toolbar" onSubmit={onSubmit}>
        <label className="pur-field">
          <span>{t("purchasing.supplier.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="pur-field">
          <span>{t("purchasing.supplier.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {t("purchasing.supplier.add")}
        </button>
      </form>
      {formError && <p className="error-text">{formError}</p>}

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
        <EmptyState title={t("purchasing.supplier.empty")} hint={t("purchasing.supplier.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="card pur-table-wrap">
          <table className="pur-table">
            <thead>
              <tr>
                <th>{t("purchasing.supplier.code")}</th>
                <th>{t("purchasing.supplier.name")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.id}>
                  <td><Bdi>{s.code}</Bdi></td>
                  <td>{s.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
