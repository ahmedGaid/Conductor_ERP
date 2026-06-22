import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { listPurchaseOrders, type PurchaseOrder } from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

const PO_STATUSES = [
  "draft",
  "confirmed",
  "partially_received",
  "received",
  "billed",
  "paid",
  "returned",
  "cancelled",
] as const;

export function PurchaseOrdersPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(() => listPurchaseOrders(), [], "purchasing:orders");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<PurchaseOrder>[]>(
    () => [
      {
        key: "status",
        label: t("common.status"),
        type: "select",
        options: PO_STATUSES.map((s) => ({ value: s, label: t(`purchasing.status.${s}`) })),
        accessor: (o) => o.status,
      },
      { key: "supplier", label: t("purchasing.orders.supplier"), type: "text", accessor: (o) => o.supplier_name },
      { key: "date", label: t("common.date"), type: "date", accessor: (o) => o.order_date },
    ],
    [t],
  );

  const filtered = useMemo(
    () => (data ? data.filter((o) => matchesAllFilters(o, fields, filters)) : data),
    [data, fields, filters],
  );

  const statusTabs = useMemo(
    () => PO_STATUSES.map((s) => ({ value: s, label: t(`purchasing.status.${s}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((o) => o.status === tab)) : filtered),
    [filtered, tab],
  );

  return (
    <section className="pur-page">
      <PurchasingNav />
      <div className="pur-page__head">
        {data && data.length > 0 && <FilterBar fields={fields} filters={filters} onChange={setFilters} />}
        <Link className="btn btn--primary" to="/purchasing/orders/new">
          {t("purchasing.tabs.newOrder")}
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
          title={t("purchasing.orders.empty")}
          hint={t("common.emptyHint")}
          action={{ label: t("purchasing.tabs.newOrder"), to: "/purchasing/orders/new" }}
        />
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={statusTabs}
          accessor={(o) => o.status}
          value={tab}
          onChange={setTab}
          ariaLabel={t("common.status")}
        />
      )}
      {data && data.length > 0 && visible && visible.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {visible && visible.length > 0 && (
        <div className="card pur-table-wrap">
          <table className="pur-table">
            <thead>
              <tr>
                <th>{t("purchasing.orders.number")}</th>
                <th>{t("purchasing.orders.supplier")}</th>
                <th>{t("common.date")}</th>
                <th>{t("common.status")}</th>
                <th className="pur-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((o) => (
                <tr key={o.id}>
                  <td>
                    <Link to={`/purchasing/orders/${o.id}`} className="latin">{o.number}</Link>
                  </td>
                  <td>{o.supplier_name}</td>
                  <td className="latin muted">{o.order_date}</td>
                  <td>
                    <span className={`pur-badge pur-badge--${o.status}`}>
                      {t(`purchasing.status.${o.status}`)}
                    </span>
                  </td>
                  <td className="pur-table__num"><Bdi>{formatMinor(o.subtotal_minor, o.currency)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
