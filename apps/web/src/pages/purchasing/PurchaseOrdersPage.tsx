import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { listPurchaseOrders, getPurchaseOrder, approvePO, confirmPO, type PurchaseOrder } from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { prefetch } from "../../lib/prefetch";
import { formatMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { RowActions } from "../../components/RowActions";
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
  const toast = useToast();
  const { data, loading, error, mutate } = useAsync(() => listPurchaseOrders(), [], "purchasing:orders");
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

  // j/k move a row highlight, Enter/o opens it on the detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<PurchaseOrder>({
    items: visible ?? [],
    onOpen: (o) => navigate(`/purchasing/orders/${o.id}`),
  });

  // One-click row actions mirror the PO-detail gating: approve a draft awaiting sign-off, then
  // confirm a draft that's ready. Heavier steps (receive/bill/payment) stay on the detail page.
  // Optimistic: patch the row in place, reconcile with the server's order, roll back + toast on
  // failure.
  function act(
    id: string,
    apply: (order: PurchaseOrder) => PurchaseOrder,
    request: () => Promise<PurchaseOrder>,
    success: string,
  ) {
    if (!data) return;
    void runOptimistic<PurchaseOrder[], PurchaseOrder>({
      current: data,
      mutate,
      optimistic: (rows) => rows.map((o) => (o.id === id ? apply(o) : o)),
      request,
      settle: (predicted, updated) => predicted.map((o) => (o.id === id ? updated : o)),
      toast,
      success,
    });
  }

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
                <th />
              </tr>
            </thead>
            <tbody>
              {visible.map((o, i) => (
                <tr key={o.id} data-kbd-active={i === active ? "true" : undefined} aria-selected={i === active}>
                  <td>
                    <Link
                      to={`/purchasing/orders/${o.id}`}
                      className="latin"
                      onMouseEnter={() => prefetch(`purchasing:order:${o.id}`, () => getPurchaseOrder(o.id))}
                      onFocus={() => prefetch(`purchasing:order:${o.id}`, () => getPurchaseOrder(o.id))}
                    >
                      {o.number}
                    </Link>
                  </td>
                  <td>{o.supplier_name}</td>
                  <td className="latin muted">{o.order_date}</td>
                  <td>
                    <span className={`pur-badge pur-badge--${o.status}`}>
                      {t(`purchasing.status.${o.status}`)}
                    </span>
                  </td>
                  <td className="pur-table__num"><Bdi>{formatMinor(o.subtotal_minor, o.currency)}</Bdi></td>
                  <td>
                    <RowActions label={t("common.actions")}>
                      {o.status === "draft" && o.requires_approval && !o.approved && (
                        <button
                          className="btn btn--sm"
                          onClick={() => act(o.id, (r) => ({ ...r, approved: true }), () => approvePO(o.id), t("purchasing.toast.approved"))}
                        >
                          {t("purchasing.detail.approve")}
                        </button>
                      )}
                      {o.status === "draft" && (!o.requires_approval || o.approved) && (
                        <button
                          className="btn btn--sm btn--primary"
                          onClick={() => act(o.id, (r) => ({ ...r, status: "confirmed" }), () => confirmPO(o.id), t("purchasing.toast.confirmed"))}
                        >
                          {t("purchasing.detail.confirm")}
                        </button>
                      )}
                    </RowActions>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
