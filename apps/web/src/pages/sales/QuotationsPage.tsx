import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { listQuotations, getQuotation, type Quotation } from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { prefetch } from "../../lib/prefetch";
import { formatMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { SalesNav } from "./SalesNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./sales.css";

const QUOTATION_STATUSES = ["draft", "submitted", "approved", "rejected", "converted", "cancelled"] as const;

export function QuotationsPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(() => listQuotations(), [], "sales:quotations");
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
  });

  return (
    <section className="sales-page">
      <SalesNav />
      <div className="sales-page__head">
        {data && data.length > 0 && <FilterBar fields={fields} filters={filters} onChange={setFilters} />}
        <Link className="btn btn--primary" to="/sales/quotations/new">
          {t("sales.tabs.newQuotation")}
        </Link>
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
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {visible && visible.length > 0 && (
        <div className="card sales-table-wrap">
          <table className="sales-table">
            <thead>
              <tr>
                <th>{t("sales.quotations.number")}</th>
                <th>{t("sales.orders.customer")}</th>
                <th>{t("common.date")}</th>
                <th>{t("common.status")}</th>
                <th className="sales-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((q, i) => (
                <tr key={q.id} data-kbd-active={i === active ? "true" : undefined} aria-selected={i === active}>
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
                    <span className={`sales-badge sales-badge--${q.status}`}>
                      {t(`sales.quotationStatus.${q.status}`)}
                    </span>
                  </td>
                  <td className="sales-table__num"><Bdi>{formatMinor(q.subtotal_minor, q.currency)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
