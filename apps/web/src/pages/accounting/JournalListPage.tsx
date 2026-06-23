import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { getJournal, listJournals, type JournalEntry } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { prefetch } from "../../lib/prefetch";
import { formatMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

export function JournalListPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(() => listJournals(), [], "accounting:journals");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<JournalEntry>[]>(
    () => [
      { key: "date", label: t("common.date"), type: "date", accessor: (e) => e.date },
      { key: "period", label: t("accounting.journals.period"), type: "text", accessor: (e) => e.period_code },
      { key: "memo", label: t("accounting.entry.memo"), type: "text", accessor: (e) => e.memo },
    ],
    [t],
  );

  const filtered = useMemo(
    () => (data ? data.filter((e) => matchesAllFilters(e, fields, filters)) : data),
    [data, fields, filters],
  );

  // j/k move a row highlight, Enter/o opens it on the detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<JournalEntry>({
    items: filtered ?? [],
    onOpen: (e) => navigate(`/accounting/journals/${e.id}`),
  });

  return (
    <section className="acct-page">
      <AccountingNav />
      <div className="acct-page__head">
        {data && data.length > 0 && <FilterBar fields={fields} filters={filters} onChange={setFilters} />}
        <Link className="btn btn--primary" to="/accounting/journals/new">
          {t("accounting.tabs.newEntry")}
        </Link>
      </div>

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
        <EmptyState
          title={t("accounting.journals.empty")}
          hint={t("common.emptyHint")}
          action={{ label: t("accounting.tabs.newEntry"), to: "/accounting/journals/new" }}
        />
      )}
      {data && data.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {filtered && filtered.length > 0 && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.journals.number")}</th>
                <th>{t("common.date")}</th>
                <th>{t("accounting.journals.period")}</th>
                <th>{t("accounting.entry.memo")}</th>
                <th className="acct-table__num">{t("accounting.journals.total")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e, i) => {
                const total = e.lines.reduce((s, l) => s + l.debit, 0);
                return (
                  <tr key={e.id} data-kbd-active={i === active ? "true" : undefined} aria-selected={i === active}>
                    <td>
                      <Link
                        to={`/accounting/journals/${e.id}`}
                        className="latin"
                        onMouseEnter={() => prefetch(`accounting:journal:${e.id}`, () => getJournal(e.id))}
                        onFocus={() => prefetch(`accounting:journal:${e.id}`, () => getJournal(e.id))}
                      >
                        {e.number}
                      </Link>
                    </td>
                    <td className="latin">{e.date}</td>
                    <td className="latin">{e.period_code}</td>
                    <td>{e.memo}</td>
                    <td className="acct-table__num">
                      <Bdi>{formatMinor(total, e.currency)}</Bdi>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
