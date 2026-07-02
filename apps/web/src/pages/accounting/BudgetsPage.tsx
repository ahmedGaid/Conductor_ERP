import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { createBudget, getBudget, listBudgets } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useFormKeys } from "../../hooks/useFormKeys";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { prefetch } from "../../lib/prefetch";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./accounting.css";

type Budget = Awaited<ReturnType<typeof listBudgets>>[number];

export function BudgetsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(listBudgets, [], "accounting:budgets");
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

  // j/k move a row highlight, Enter/o opens it on the detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<Budget>({
    items: filtered ?? [],
    onOpen: (b) => navigate(`/accounting/budgets/${b.id}`),
    persistKey: "accounting:budgets",
    getItemId: (b) => b.id,
  });

  const [name, setName] = useState("");
  const [fy, setFy] = useState(String(new Date().getFullYear()));

  // ⌘/Ctrl+Enter submits the add form from any field.
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

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

      <form ref={formRef} className="card acct-toolbar" onSubmit={onSubmit}>
        <label className="acct-field grow">
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
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

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
              {filtered.map((b, i) => (
                <tr key={b.id} data-kbd-active={i === active ? "true" : undefined} aria-selected={i === active}>
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
