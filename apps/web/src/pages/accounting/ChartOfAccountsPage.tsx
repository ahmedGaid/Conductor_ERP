import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createAccount, listAccounts, type AccountType } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { Bdi } from "../../components/Bdi";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

const TYPES: AccountType[] = ["asset", "liability", "equity", "income", "expense"];

export function ChartOfAccountsPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listAccounts, [], "accounting:accounts");

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [type, setType] = useState<AccountType>("asset");
  const [postable, setPostable] = useState(true);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      await createAccount({ code, name, type, is_postable: postable });
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
          <span>{t("accounting.account.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="acct-field">
          <span>{t("accounting.account.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="acct-field">
          <span>{t("accounting.account.type")}</span>
          <select value={type} onChange={(e) => setType(e.target.value as AccountType)}>
            {TYPES.map((ty) => (
              <option key={ty} value={ty}>
                {t(`accounting.types.${ty}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="acct-field">
          <span>{t("accounting.account.postable")}</span>
          <input
            type="checkbox"
            checked={postable}
            onChange={(e) => setPostable(e.target.checked)}
          />
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {t("accounting.account.add")}
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

      {data && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.account.code")}</th>
                <th>{t("accounting.account.name")}</th>
                <th>{t("accounting.account.type")}</th>
                <th>{t("accounting.account.postable")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((a) => (
                <tr key={a.id}>
                  <td>
                    <Bdi>{a.code}</Bdi>
                  </td>
                  <td>{a.name}</td>
                  <td>{t(`accounting.types.${a.type}`)}</td>
                  <td>{a.is_postable ? t("common.yes") : t("common.no")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
