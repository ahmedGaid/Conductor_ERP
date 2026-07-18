import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createAccount, listAccounts, type Account, type AccountType } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
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
  const savedViews = useSavedViews({ listKey: "accounting:accounts", fields, filters, setFilters });
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

  // Add is a form (forms keep their controls) — no bar primary, just print + CSV.
  const csvColumns = useMemo<CsvColumn<Account>[]>(
    () => [
      { header: t("accounting.account.code"), accessor: (a) => a.code },
      { header: t("accounting.account.name"), accessor: (a) => a.name },
      { header: t("accounting.account.type"), accessor: (a) => t(`accounting.types.${a.type}`) },
      { header: t("accounting.account.postable"), accessor: (a) => (a.is_postable ? t("common.yes") : t("common.no")) },
    ],
    [t],
  );
  useListPageActions({ rows: visible, columns: csvColumns, filename: "chart-of-accounts" });

  // Multi-select for bulk CSV export (no other bulk verb applies; no detail page, so no keyboard nav).
  const selection = useRowSelection<Account>({
    items: visible ?? [],
    getItemId: (a) => a.id,
  });

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
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("accounting.account.empty")} hint={t("accounting.account.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="acct-filters">
          <SavedViews api={savedViews} />
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
        <EmptyState
          title={t("filter.noMatch")}
          hint={t("filter.noMatchHint")}
          action={{ label: t("filter.clearAll"), onClick: () => setFilters([]) }}
        />
      )}

      {visible && visible.length > 0 && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <SelectAllCell
                  className="acct-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("accounting.account.code")}</th>
                <th>{t("accounting.account.name")}</th>
                <th>{t("accounting.account.type")}</th>
                <th>{t("accounting.account.postable")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((a, i) => (
                <tr key={a.id} data-selected={selection.isSelected(a.id) ? "true" : undefined} aria-selected={selection.isSelected(a.id)}>
                  <SelectRowCell
                    className="acct-table__select"
                    checked={selection.isSelected(a.id)}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
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

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("chart-of-accounts-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
