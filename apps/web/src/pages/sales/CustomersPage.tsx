import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createCustomer, listCustomers } from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { SalesNav } from "./SalesNav";
import "./sales.css";

export function CustomersPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listCustomers, []);

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [limit, setLimit] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      const credit = parseToMinor(limit) ?? 0;
      await createCustomer({ code, name, credit_limit_minor: credit });
      setCode("");
      setName("");
      setLimit("");
      reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="sales-page">
      <h1>{t("nav.sales")}</h1>
      <SalesNav />

      <form className="card sales-toolbar" onSubmit={onSubmit}>
        <label className="sales-field">
          <span>{t("sales.customer.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="sales-field">
          <span>{t("sales.customer.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="sales-field">
          <span>{t("sales.customer.creditLimit")}</span>
          <input className="latin" inputMode="decimal" value={limit} onChange={(e) => setLimit(e.target.value)} placeholder="0.00" />
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {t("sales.customer.add")}
        </button>
      </form>
      {formError && <p className="error-text">{formError}</p>}

      {loading && <p className="muted">{t("common.loading")}</p>}
      {error && <p className="error-text">{error}</p>}

      {data && (
        <div className="card sales-table-wrap">
          <table className="sales-table">
            <thead>
              <tr>
                <th>{t("sales.customer.code")}</th>
                <th>{t("sales.customer.name")}</th>
                <th className="sales-table__num">{t("sales.customer.creditLimit")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id}>
                  <td><Bdi>{c.code}</Bdi></td>
                  <td>{c.name}</td>
                  <td className="sales-table__num">
                    <Bdi>{c.credit_limit_minor ? formatMinor(c.credit_limit_minor) : t("sales.customer.unlimited")}</Bdi>
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
