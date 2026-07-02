import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { listPurchaseOrders, getPurchaseOrder, approvePO, confirmPO, type PurchaseOrder } from "../../api/purchasing";
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
import { purchasingTone } from "../../lib/statusTone";
import { PartyLink } from "../../components/PartyLink";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { RowActions } from "../../components/RowActions";
import { PurchasingNav } from "./PurchasingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
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
  const { data, loading, error, reload, mutate } = useAsync(() => listPurchaseOrders(), [], "purchasing:orders");
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
    persistKey: "purchasing:orders",
    getItemId: (o) => o.id,
  });

  // Multi-select for bulk approve/confirm, mirroring the per-row gating below.
  const selection = useRowSelection<PurchaseOrder>({
    items: visible ?? [],
    getItemId: (o) => o.id,
    activeIndex: active,
  });
  const approvable = selection.selectedItems.filter((o) => o.status === "draft" && o.requires_approval && !o.approved);
  const confirmable = selection.selectedItems.filter((o) => o.status === "draft" && (!o.requires_approval || o.approved));

  // Run one verb across many rows in a single optimistic pass, then clear the selection.
  function bulkAct(targets: PurchaseOrder[], apply: (o: PurchaseOrder) => PurchaseOrder, request: (id: string) => Promise<PurchaseOrder>, success: string) {
    if (targets.length === 0) return;
    const ids = new Set(targets.map((o) => o.id));
    void runOptimistic<PurchaseOrder[], PurchaseOrder[]>({
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
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
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
                <th className="pur-table__select">
                  <Checkbox
                    checked={selection.allSelected}
                    indeterminate={selection.someSelected}
                    onChange={() => selection.toggleAll()}
                    label={t("bulk.selectAll")}
                  />
                </th>
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
                <tr
                  key={o.id}
                  data-kbd-active={i === active ? "true" : undefined}
                  data-selected={selection.isSelected(o.id) ? "true" : undefined}
                  aria-selected={selection.isSelected(o.id) || i === active}
                >
                  <td className="pur-table__select">
                    <Checkbox
                      checked={selection.isSelected(o.id)}
                      onChange={(_next, shiftKey) => selection.toggle(i, shiftKey)}
                      label={t("bulk.selectRow")}
                    />
                  </td>
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
                  <td><PartyLink type="supplier" code={o.supplier_code}>{o.supplier_name}</PartyLink></td>
                  <td className="latin muted">{o.order_date}</td>
                  <td>
                    <Badge tone={purchasingTone(o.status)}>{t(`purchasing.status.${o.status}`)}</Badge>
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

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        {approvable.length > 0 && (
          <button
            className="btn btn--sm"
            onClick={() =>
              bulkAct(
                approvable,
                (r) => ({ ...r, approved: true }),
                (id) => approvePO(id),
                t(approvable.length === 1 ? "purchasing.toast.bulkApprovedOne" : "purchasing.toast.bulkApproved", { count: approvable.length }),
              )
            }
          >
            {t("purchasing.detail.approve")}
          </button>
        )}
        {confirmable.length > 0 && (
          <button
            className="btn btn--sm"
            onClick={() =>
              bulkAct(
                confirmable,
                (r) => ({ ...r, status: "confirmed" }),
                (id) => confirmPO(id),
                t(confirmable.length === 1 ? "purchasing.toast.bulkConfirmedOne" : "purchasing.toast.bulkConfirmed", { count: confirmable.length }),
              )
            }
          >
            {t("purchasing.detail.confirm")}
          </button>
        )}
      </BulkActionBar>
    </section>
  );
}
