import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { listQuotations, getQuotation, submitQuotation, approveQuotation, type Quotation } from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { prefetch } from "../../lib/prefetch";
import { formatMinor } from "../../lib/money";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { Badge, type BadgeTone } from "../../components/Badge";
import { StatusRing } from "../../components/StatusRing";
import { salesTone } from "../../lib/statusTone";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { SalesNav } from "./SalesNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./sales.css";

const QUOTATION_STATUSES = ["draft", "submitted", "approved", "rejected", "converted", "cancelled"] as const;

const MS_PER_DAY = 1000 * 60 * 60 * 24;

function daysUntil(dateStr: string): number {
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / MS_PER_DAY);
}

function validityTone(days: number): BadgeTone {
  if (days < 0) return "failed";
  if (days <= 7) return "waiting";
  return "neutral";
}

// Only an open (still-acceptable) quotation has a validity worth flagging.
const OPEN_STATUSES = new Set(["draft", "submitted", "approved"]);

export function QuotationsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(() => listQuotations(), [], "sales:quotations");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<Quotation>[]>(
    () => [
      {
        key: "status",
        label: t("common.status"),
        type: "select",
        options: QUOTATION_STATUSES.map((s) => ({ value: s, label: t(`sales.quotationStatus.${s}`) })),
        accessor: (q) => q.status,
      },
      { key: "customer", label: t("sales.orders.customer"), type: "text", accessor: (q) => q.customer_name },
      { key: "date", label: t("common.date"), type: "date", accessor: (q) => q.quote_date },
    ],
    [t],
  );
  const savedViews = useSavedViews({ listKey: "sales:quotations", fields, filters, setFilters });

  const filtered = useMemo(
    () => (data ? data.filter((q) => matchesAllFilters(q, fields, filters)) : data),
    [data, fields, filters],
  );

  const statusTabs = useMemo(
    () => QUOTATION_STATUSES.map((s) => ({ value: s, label: t(`sales.quotationStatus.${s}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((q) => q.status === tab)) : filtered),
    [filtered, tab],
  );

  // j/k move a row highlight, Enter/o opens it on the detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<Quotation>({
    items: visible ?? [],
    onOpen: (q) => navigate(`/sales/quotations/${q.id}`),
    persistKey: "sales:quotations",
    getItemId: (q) => q.id,
  });

  // Multi-select for bulk submit/approve. `x` toggles active row; ⌘A all; Esc clears.
  const selection = useRowSelection<Quotation>({
    items: visible ?? [],
    getItemId: (q) => q.id,
    activeIndex: active,
  });
  const submittable = selection.selectedItems.filter((q) => q.status === "draft");
  const approvable = selection.selectedItems.filter((q) => q.status === "submitted");

  const csvColumns = useMemo<CsvColumn<Quotation>[]>(
    () => [
      { header: t("sales.quotations.number"), accessor: (q) => q.number },
      { header: t("sales.orders.customer"), accessor: (q) => q.customer_name },
      { header: t("common.date"), accessor: (q) => q.quote_date },
      { header: t("common.status"), accessor: (q) => t(`sales.quotationStatus.${q.status}`) },
      { header: t("sales.quotations.validUntil"), accessor: (q) => q.validity_until ?? "" },
      { header: t("sales.orders.total"), accessor: (q) => formatMinor(q.subtotal_minor, q.currency) },
    ],
    [t],
  );
  const listPrimary = useMemo(
    () => ({ label: t("sales.tabs.newQuotation"), onClick: () => navigate("/sales/quotations/new") }),
    [t, navigate],
  );
  useListPageActions({ primary: listPrimary, rows: visible, columns: csvColumns, filename: "sales-quotations" });

  // Run one lifecycle verb across many quotations in a single optimistic pass, then clear the selection.
  function bulkAct(targets: Quotation[], status: Quotation["status"], request: (id: string) => Promise<Quotation>, success: string) {
    if (targets.length === 0) return;
    const ids = new Set(targets.map((q) => q.id));
    void runOptimistic<Quotation[], Quotation[]>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows.map((q) => (ids.has(q.id) ? { ...q, status } : q)),
      request: () => Promise.all(targets.map((q) => request(q.id))),
      settle: (rows, updated) => {
        const byId = new Map(updated.map((u) => [u.id, u]));
        return rows.map((q) => byId.get(q.id) ?? q);
      },
      toast,
      success,
    });
    selection.clear();
  }

  return (
    <section className="sales-page">
      <SalesNav />
      <div className="sales-page__head">
        {data && data.length > 0 && (
          <>
            <SavedViews api={savedViews} />
            <FilterBar fields={fields} filters={filters} onChange={setFilters} />
          </>
        )}
      </div>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <EmptyState
          title={t("sales.quotations.empty")}
          hint={t("common.emptyHint")}
          action={{ label: t("sales.tabs.newQuotation"), to: "/sales/quotations/new" }}
        />
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={statusTabs}
          accessor={(q) => q.status}
          value={tab}
          onChange={setTab}
          ariaLabel={t("common.status")}
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
        <div className="card sales-table-wrap">
          <table className="sales-table">
            <thead>
              <tr>
                <SelectAllCell
                  className="sales-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("sales.quotations.number")}</th>
                <th>{t("sales.orders.customer")}</th>
                <th>{t("common.date")}</th>
                <th>{t("common.status")}</th>
                <th>{t("sales.quotations.validUntil")}</th>
                <th className="sales-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((q, i) => (
                <tr
                  key={q.id}
                  data-kbd-active={i === active ? "true" : undefined}
                  data-selected={selection.isSelected(q.id) ? "true" : undefined}
                  aria-selected={selection.isSelected(q.id) || i === active}
                >
                  <SelectRowCell
                    className="sales-table__select"
                    checked={selection.isSelected(q.id)}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
                  <td>
                    <Link
                      to={`/sales/quotations/${q.id}`}
                      className="latin"
                      onMouseEnter={() => prefetch(`sales:quotation:${q.id}`, () => getQuotation(q.id))}
                      onFocus={() => prefetch(`sales:quotation:${q.id}`, () => getQuotation(q.id))}
                    >
                      {q.number}
                    </Link>
                  </td>
                  <td>{q.customer_name}</td>
                  <td className="latin muted">{q.quote_date}</td>
                  <td>
                    <StatusRing
                      docType="quotation"
                      status={q.status}
                      tone={salesTone(q.status)}
                      label={t(`sales.quotationStatus.${q.status}`)}
                    />
                  </td>
                  <td className="latin muted">
                    {q.validity_until && OPEN_STATUSES.has(q.status) ? (
                      <Badge tone={validityTone(daysUntil(q.validity_until))}>{q.validity_until}</Badge>
                    ) : (
                      q.validity_until ?? "—"
                    )}
                  </td>
                  <td className="sales-table__num"><Bdi>{formatMinor(q.subtotal_minor, q.currency)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        {submittable.length > 0 && (
          <button
            className="btn btn--sm"
            onClick={() =>
              bulkAct(
                submittable,
                "submitted",
                (id) => submitQuotation(id),
                t(submittable.length === 1 ? "sales.toast.bulkQuoteSubmittedOne" : "sales.toast.bulkQuoteSubmitted", { count: submittable.length }),
              )
            }
          >
            {t("sales.quotations.submit")}
          </button>
        )}
        {approvable.length > 0 && (
          <button
            className="btn btn--sm"
            onClick={() =>
              bulkAct(
                approvable,
                "approved",
                (id) => approveQuotation(id),
                t(approvable.length === 1 ? "sales.toast.bulkQuoteApprovedOne" : "sales.toast.bulkQuoteApproved", { count: approvable.length }),
              )
            }
          >
            {t("sales.quotations.approve")}
          </button>
        )}
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("sales-quotations-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
