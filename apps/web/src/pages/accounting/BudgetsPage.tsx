import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { createBudget, getBudget, listBudgets } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { prefetch } from "../../lib/prefetch";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

type Budget = Awaited<ReturnType<typeof listBudgets>>[number];

export function BudgetsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, mutate } = useAsync(listBudgets, [], "accounting:budgets");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<Budget>[]>(
    () => [
      { key: "name", label: t("accounting.budgets.name"), type: "text", accessor: (b) => b.name },
      { key: "fy", label: t("accounting.budgets.fiscalYear"), type: "text", accessor: (b) => b.fiscal_year_code },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((b) => matchesAllFilters(b, fields, filters)) : data),
    [data, fields, filters],
  );

  const [name, setName] = useState("");
  const [fy, setFy] = useState(String(new Date().getFullYear()));

  // Optimistic create: show the new budget instantly and clear the name for the next entry; the
  // server row replaces the placeholder on settle, or it rolls back + toasts.
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const n = name.trim();
    const f = fy.trim();
    if (!n || !f) return;
    void optimisticCreate<Budget>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, name: n, fiscal_year_code: f, is_active: true }) as Budget,
      request: () => createBudget({ name: n, fiscal_year_code: f }),
      toast,
      success: t("accounting.toast.budgetCreated"),
    });
    setName("");
  }

  return (
    <section className="acct-page">
      <AccountingNav />

      <form className="card acct-toolbar" onSubmit={onSubmit}>
        <label className="acct-field" style={{ flex: 1 }}>
          <span>{t("accounting.budgets.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="acct-field">
          <span>{t("accounting.budgets.fiscalYear")}</span>
          <input className="latin" value={fy} onChange={(e) => setFy(e.target.value)} required />
        </label>
        <button className="btn btn--primary" type="submit">
          {t("accounting.budgets.add")}
        </button>
      </form>

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
        <EmptyState title={t("accounting.budgets.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="acct-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {filtered && filtered.length > 0 && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.budgets.name")}</th>
                <th>{t("accounting.budgets.fiscalYear")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((b) => (
                <tr key={b.id}>
                  <td>
                    <Link
                      className="acct-link"
                      to={`/accounting/budgets/${b.id}`}
                      onMouseEnter={() => prefetch(`accounting:budget:${b.id}`, () => getBudget(b.id))}
                      onFocus={() => prefetch(`accounting:budget:${b.id}`, () => getBudget(b.id))}
                    >
                      {b.name}
                    </Link>
                  </td>
                  <td><Bdi>{b.fiscal_year_code}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
