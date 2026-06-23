import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createAccount, listAccounts, type Account, type AccountType } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

const TYPES: AccountType[] = ["asset", "liability", "equity", "income", "expense"];

export function ChartOfAccountsPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listAccounts, [], "accounting:accounts");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<Account>[]>(
    () => [
      { key: "code", label: t("accounting.account.code"), type: "text", accessor: (a) => a.code },
      { key: "name", label: t("accounting.account.name"), type: "text", accessor: (a) => a.name },
      {
        key: "type",
        label: t("accounting.account.type"),
        type: "select",
        options: TYPES.map((ty) => ({ value: ty, label: t(`accounting.types.${ty}`) })),
        accessor: (a) => a.type,
      },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((a) => matchesAllFilters(a, fields, filters)) : data),
    [data, fields, filters],
  );

  const typeTabs = useMemo(
    () => TYPES.map((ty) => ({ value: ty, label: t(`accounting.types.${ty}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((a) => a.type === tab)) : filtered),
    [filtered, tab],
  );

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
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("accounting.account.empty")} hint={t("accounting.account.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="acct-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={typeTabs}
          accessor={(a) => a.type}
          value={tab}
          onChange={setTab}
          ariaLabel={t("accounting.account.type")}
        />
      )}
      {data && data.length > 0 && visible && visible.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {visible && visible.length > 0 && (
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
              {visible.map((a) => (
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
