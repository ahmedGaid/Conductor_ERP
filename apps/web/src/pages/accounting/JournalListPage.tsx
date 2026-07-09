import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { getJournal, listJournals, type JournalEntry } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { prefetch } from "../../lib/prefetch";
import { formatMinor } from "../../lib/money";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { PartyLink, type PartyType } from "../../components/PartyLink";
import { StatusRing } from "../../components/StatusRing";
import { journalTone } from "../../lib/statusTone";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
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
    persistKey: "accounting:journals",
    getItemId: (e) => e.id,
  });

  const csvColumns = useMemo<CsvColumn<JournalEntry>[]>(
    () => [
      { header: t("accounting.journals.number"), accessor: (e) => e.number },
      { header: t("common.date"), accessor: (e) => e.date },
      { header: t("accounting.journals.period"), accessor: (e) => e.period_code },
      { header: t("accounting.entry.memo"), accessor: (e) => e.memo },
      { header: t("common.status"), accessor: (e) => t(`accounting.journalStatus.${e.status}`) },
      {
        header: t("accounting.journals.total"),
        accessor: (e) => formatMinor(e.lines.reduce((s, l) => s + l.debit, 0), e.currency),
      },
    ],
    [t],
  );
  const listPrimary = useMemo(
    () => ({ label: t("accounting.tabs.newEntry"), onClick: () => navigate("/accounting/journals/new") }),
    [t, navigate],
  );
  useListPageActions({ primary: listPrimary, rows: filtered, columns: csvColumns, filename: "journal-entries" });

  // Multi-select for bulk CSV export (journals are posted on creation — no other bulk verb applies).
  const selection = useRowSelection<JournalEntry>({
    items: filtered ?? [],
    getItemId: (e) => e.id,
    activeIndex: active,
  });

  return (
    <section className="acct-page">
      <AccountingNav />
      <div className="acct-page__head">
        {data && data.length > 0 && <FilterBar fields={fields} filters={filters} onChange={setFilters} />}
      </div>

      {loading && (
        <ListSkeleton />
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
                <SelectAllCell
                  className="acct-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("accounting.journals.number")}</th>
                <th>{t("common.date")}</th>
                <th>{t("accounting.journals.period")}</th>
                <th>{t("accounting.entry.memo")}</th>
                <th>{t("common.status")}</th>
                <th className="acct-table__num">{t("accounting.journals.total")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e, i) => {
                const total = e.lines.reduce((s, l) => s + l.debit, 0);
                return (
                  <tr
                    key={e.id}
                    data-kbd-active={i === active ? "true" : undefined}
                    data-selected={selection.isSelected(e.id) ? "true" : undefined}
                    aria-selected={selection.isSelected(e.id) || i === active}
                  >
                    <SelectRowCell
                      className="acct-table__select"
                      checked={selection.isSelected(e.id)}
                      onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                    />
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
                    <td>
                      {e.party_code ? (
                        <PartyLink type={e.party_type as PartyType} code={e.party_code}>
                          {e.memo}
                        </PartyLink>
                      ) : (
                        e.memo
                      )}
                    </td>
                    <td>
                      <StatusRing
                        docType="journal"
                        status={e.status}
                        tone={journalTone(e.status)}
                        label={t(`accounting.journalStatus.${e.status}`)}
                      />
                    </td>
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

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("journal-entries-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
