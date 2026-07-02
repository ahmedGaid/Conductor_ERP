import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { listOrders, getOrder, approveOrder, confirmOrder, type SalesOrder } from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useRowSelection } from "../../hooks/useRowSelection";
import { Checkbox } from "../../components/Checkbox";
import { BulkActionBar } from "../../components/BulkActionBar";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { prefetch } from "../../lib/prefetch";
import { formatMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { Badge } from "../../components/Badge";
import { salesTone } from "../../lib/statusTone";
import { PartyLink } from "../../components/PartyLink";
import { EmptyState } from "../../components/EmptyState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { RowActions } from "../../components/RowActions";
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
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(() => listOrders(), [], "sales:orders");
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

  // j/k move a row highlight, Enter/o opens it on the detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<SalesOrder>({
    items: visible ?? [],
    onOpen: (o) => navigate(`/sales/orders/${o.id}`),
    persistKey: "sales:orders",
    getItemId: (o) => o.id,
  });

  // Multi-select for bulk approve/confirm. `x` toggles the active row; ⌘A selects all; Esc clears.
  const selection = useRowSelection<SalesOrder>({
    items: visible ?? [],
    getItemId: (o) => o.id,
    activeIndex: active,
  });

  // Which selected drafts each bulk verb can act on, mirroring the per-row gating.
  const approvable = selection.selectedItems.filter((o) => o.status === "draft" && o.requires_approval && !o.approved);
  const confirmable = selection.selectedItems.filter((o) => o.status === "draft" && (!o.requires_approval || o.approved));

  // Run one verb across many rows in a single optimistic pass: predict every target row, fire the
  // requests together, reconcile each with its server row, then clear the selection.
  function bulkAct(targets: SalesOrder[], apply: (o: SalesOrder) => SalesOrder, request: (id: string) => Promise<SalesOrder>, success: string) {
    if (targets.length === 0) return;
    const ids = new Set(targets.map((o) => o.id));
    void runOptimistic<SalesOrder[], SalesOrder[]>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows.map((o) => (ids.has(o.id) ? apply(o) : o)),
      request: () => Promise.all(targets.map((o) => request(o.id))),
      settle: (rows, updated) => {
        const byId = new Map(updated.map((u) => [u.id, u]));
        return rows.map((o) => byId.get(o.id) ?? o);
      },
      toast,
      success,
    });
    selection.clear();
  }

  // One-click row actions mirror the order-detail gating: approve a draft awaiting sign-off, then
  // confirm a draft that's ready. Heavier steps (deliver/invoice/payment) stay on the detail page.
  //
  // Optimistic: the row updates the instant you click (the matching button disappears as its
  // gating condition flips), the request runs in the background, the server's canonical row is
  // reconciled on success, and a failure rolls the row back with an error toast — no spinner, no
  // full-list refetch for the user's own action.
  function act(id: string, apply: (order: SalesOrder) => SalesOrder, request: () => Promise<SalesOrder>, success: string) {
    void runOptimistic<SalesOrder[], SalesOrder>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows.map((o) => (o.id === id ? apply(o) : o)),
      request,
      settle: (rows, updated) => rows.map((o) => (o.id === updated.id ? updated : o)),
      toast,
      success,
    });
  }

  return (
    <section className="sales-page">
      <SalesNav />
      <div className="sales-page__head">
        {data && data.length > 0 && <FilterBar fields={fields} filters={filters} onChange={setFilters} />}
        <Link className="btn btn--primary sales-page__head-cta" to="/sales/orders/new">
          {t("sales.tabs.newOrder")}
        </Link>
      </div>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}
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
                <th className="sales-table__select">
                  <Checkbox
                    checked={selection.allSelected}
                    indeterminate={selection.someSelected}
                    onChange={() => selection.toggleAll()}
                    label={t("bulk.selectAll")}
                  />
                </th>
                <th>{t("sales.orders.number")}</th>
                <th>{t("sales.orders.customer")}</th>
                <th>{t("sales.orders.date")}</th>
                <th>{t("sales.orders.status")}</th>
                <th className="sales-table__num">{t("sales.orders.total")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {visible.map((o, i) => (
                <tr
                  key={o.id}
                  data-kbd-active={i === active ? "true" : undefined}
                  data-selected={selection.isSelected(o.id) ? "true" : undefined}
                  aria-selected={selection.isSelected(o.id) || i === active}
                >
                  <td className="sales-table__select">
                    <Checkbox
                      checked={selection.isSelected(o.id)}
                      onChange={(_next, shiftKey) => selection.toggle(i, shiftKey)}
                      label={t("bulk.selectRow")}
                    />
                  </td>
                  <td>
                    <Link
                      to={`/sales/orders/${o.id}`}
                      className="latin"
                      onMouseEnter={() => prefetch(`sales:order:${o.id}`, () => getOrder(o.id))}
                      onFocus={() => prefetch(`sales:order:${o.id}`, () => getOrder(o.id))}
                    >
                      {o.number}
                    </Link>
                  </td>
                  <td><PartyLink type="customer" code={o.customer_code}>{o.customer_name}</PartyLink></td>
                  <td className="latin muted">{o.order_date}</td>
                  <td>
                    <Badge tone={salesTone(o.status)}>{t(`sales.status.${o.status}`)}</Badge>
                  </td>
                  <td className="sales-table__num"><Bdi>{formatMinor(o.subtotal_minor, o.currency)}</Bdi></td>
                  <td>
                    <RowActions label={t("common.actions")}>
                      {o.status === "draft" && o.requires_approval && !o.approved && (
                        <button
                          className="btn btn--sm"
                          onClick={() =>
                            act(o.id, (r) => ({ ...r, approved: true }), () => approveOrder(o.id), t("sales.toast.approved"))
                          }
                        >
                          {t("sales.detail.approve")}
                        </button>
                      )}
                      {o.status === "draft" && (!o.requires_approval || o.approved) && (
                        <button
                          className="btn btn--sm btn--primary"
                          onClick={() =>
                            act(o.id, (r) => ({ ...r, status: "confirmed" }), () => confirmOrder(o.id), t("sales.toast.confirmed"))
                          }
                        >
                          {t("sales.detail.confirm")}
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

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        {approvable.length > 0 && (
          <button
            className="btn btn--sm"
            onClick={() =>
              bulkAct(
                approvable,
                (r) => ({ ...r, approved: true }),
                (id) => approveOrder(id),
                t(approvable.length === 1 ? "sales.toast.bulkApprovedOne" : "sales.toast.bulkApproved", { count: approvable.length }),
              )
            }
          >
            {t("sales.detail.approve")}
          </button>
        )}
        {confirmable.length > 0 && (
          <button
            className="btn btn--sm"
            onClick={() =>
              bulkAct(
                confirmable,
                (r) => ({ ...r, status: "confirmed" }),
                (id) => confirmOrder(id),
                t(confirmable.length === 1 ? "sales.toast.bulkConfirmedOne" : "sales.toast.bulkConfirmed", { count: confirmable.length }),
              )
            }
          >
            {t("sales.detail.confirm")}
          </button>
        )}
      </BulkActionBar>
    </section>
  );
}
