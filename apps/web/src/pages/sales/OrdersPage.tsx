import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { listOrders, type SalesOrder } from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { SalesNav } from "./SalesNav";
import "./sales.css";

// The order lifecycle states, shown as a "select" filter. Display words come from i18n (sales.status.*).
const ORDER_STATUSES = [
  "draft",
  "confirmed",
  "partially_delivered",
  "delivered",
  "invoiced",
  "paid",
  "returned",
  "cancelled",
] as const;

export function OrdersPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(() => listOrders(), [], "sales:orders");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<SalesOrder>[]>(
    () => [
      {
        key: "status",
        label: t("sales.orders.status"),
        type: "select",
        options: ORDER_STATUSES.map((s) => ({ value: s, label: t(`sales.status.${s}`) })),
        accessor: (o) => o.status,
      },
      {
        key: "customer",
        label: t("sales.orders.customer"),
        type: "text",
        accessor: (o) => o.customer_name,
      },
      {
        key: "date",
        label: t("sales.orders.date"),
        type: "date",
        accessor: (o) => o.order_date,
      },
    ],
    [t],
  );

  const filtered = useMemo(
    () => (data ? data.filter((o) => matchesAllFilters(o, fields, filters)) : data),
    [data, fields, filters],
  );

  // Status tabs are a quick cut on top of the FilterBar result; counts come from `filtered`.
  const statusTabs = useMemo(
    () => ORDER_STATUSES.map((s) => ({ value: s, label: t(`sales.status.${s}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((o) => o.status === tab)) : filtered),
    [filtered, tab],
  );

  return (
    <section className="sales-page">
      <SalesNav />
      <div className="sales-page__head">
        {data && data.length > 0 && <FilterBar fields={fields} filters={filters} onChange={setFilters} />}
        <Link className="btn btn--primary sales-page__head-cta" to="/sales/orders/new">
          {t("sales.tabs.newOrder")}
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
      {error && <p className="error-text">{error}</p>}
      {data && data.length === 0 && (
        <EmptyState
          title={t("sales.orders.empty")}
          hint={t("common.emptyHint")}
          action={{ label: t("sales.tabs.newOrder"), to: "/sales/orders/new" }}
        />
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={statusTabs}
          accessor={(o) => o.status}
          value={tab}
          onChange={setTab}
          ariaLabel={t("sales.orders.status")}
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
                <th>{t("sales.orders.number")}</th>
                <th>{t("sales.orders.customer")}</th>
                <th>{t("sales.orders.date")}</th>
                <th>{t("sales.orders.status")}</th>
                <th className="sales-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((o) => (
                <tr key={o.id}>
                  <td>
                    <Link to={`/sales/orders/${o.id}`} className="latin">{o.number}</Link>
                  </td>
                  <td>{o.customer_name}</td>
                  <td className="latin muted">{o.order_date}</td>
                  <td>
                    <span className={`sales-badge sales-badge--${o.status}`}>
                      {t(`sales.status.${o.status}`)}
                    </span>
                  </td>
                  <td className="sales-table__num"><Bdi>{formatMinor(o.subtotal_minor, o.currency)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
