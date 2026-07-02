import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { listRequests, getRequest, submitRequest, approveRequest, type PurchaseRequest } from "../../api/purchasing";
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
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { PurchasingNav } from "./PurchasingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./purchasing.css";

const PR_STATUSES = ["draft", "submitted", "approved", "rejected", "converted", "cancelled"] as const;

export function PurchaseRequestsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(() => listRequests(), [], "purchasing:requests");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<PurchaseRequest>[]>(
    () => [
      {
        key: "status",
        label: t("common.status"),
        type: "select",
        options: PR_STATUSES.map((s) => ({ value: s, label: t(`purchasing.requestStatus.${s}`) })),
        accessor: (r) => r.status,
      },
      { key: "supplier", label: t("purchasing.orders.supplier"), type: "text", accessor: (r) => r.supplier_name },
      { key: "date", label: t("common.date"), type: "date", accessor: (r) => r.request_date },
    ],
    [t],
  );

  const filtered = useMemo(
    () => (data ? data.filter((r) => matchesAllFilters(r, fields, filters)) : data),
    [data, fields, filters],
  );

  const statusTabs = useMemo(
    () => PR_STATUSES.map((s) => ({ value: s, label: t(`purchasing.requestStatus.${s}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((r) => r.status === tab)) : filtered),
    [filtered, tab],
  );

  // j/k move a row highlight, Enter/o opens it on the detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<PurchaseRequest>({
    items: visible ?? [],
    onOpen: (r) => navigate(`/purchasing/requests/${r.id}`),
    persistKey: "purchasing:requests",
    getItemId: (r) => r.id,
  });

  // Multi-select for bulk submit/approve, gated to the request lifecycle.
  const selection = useRowSelection<PurchaseRequest>({
    items: visible ?? [],
    getItemId: (r) => r.id,
    activeIndex: active,
  });
  const submittable = selection.selectedItems.filter((r) => r.status === "draft");
  const approvable = selection.selectedItems.filter((r) => r.status === "submitted");

  // Run one lifecycle verb across many requests in a single optimistic pass, then clear the selection.
  function bulkAct(targets: PurchaseRequest[], status: PurchaseRequest["status"], request: (id: string) => Promise<PurchaseRequest>, success: string) {
    if (targets.length === 0) return;
    const ids = new Set(targets.map((r) => r.id));
    void runOptimistic<PurchaseRequest[], PurchaseRequest[]>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows.map((r) => (ids.has(r.id) ? { ...r, status } : r)),
      request: () => Promise.all(targets.map((r) => request(r.id))),
      settle: (rows, updated) => {
        const byId = new Map(updated.map((u) => [u.id, u]));
        return rows.map((r) => byId.get(r.id) ?? r);
      },
      toast,
      success,
    });
    selection.clear();
  }

  return (
    <section className="pur-page">
      <PurchasingNav />
      <div className="pur-page__head">
        {data && data.length > 0 && <FilterBar fields={fields} filters={filters} onChange={setFilters} />}
        <Link className="btn btn--primary" to="/purchasing/requests/new">
          {t("purchasing.tabs.newRequest")}
        </Link>
      </div>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <EmptyState
          title={t("purchasing.requests.empty")}
          hint={t("common.emptyHint")}
          action={{ label: t("purchasing.tabs.newRequest"), to: "/purchasing/requests/new" }}
        />
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={statusTabs}
          accessor={(r) => r.status}
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
                <th>{t("purchasing.requests.number")}</th>
                <th>{t("purchasing.orders.supplier")}</th>
                <th>{t("common.date")}</th>
                <th>{t("common.status")}</th>
                <th className="pur-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((r, i) => (
                <tr
                  key={r.id}
                  data-kbd-active={i === active ? "true" : undefined}
                  data-selected={selection.isSelected(r.id) ? "true" : undefined}
                  aria-selected={selection.isSelected(r.id) || i === active}
                >
                  <td className="pur-table__select">
                    <Checkbox
                      checked={selection.isSelected(r.id)}
                      onChange={(_next, shiftKey) => selection.toggle(i, shiftKey)}
                      label={t("bulk.selectRow")}
                    />
                  </td>
                  <td>
                    <Link
                      to={`/purchasing/requests/${r.id}`}
                      className="latin"
                      onMouseEnter={() => prefetch(`purchasing:request:${r.id}`, () => getRequest(r.id))}
                      onFocus={() => prefetch(`purchasing:request:${r.id}`, () => getRequest(r.id))}
                    >
                      {r.number}
                    </Link>
                  </td>
                  <td>{r.supplier_name}</td>
                  <td className="latin muted">{r.request_date}</td>
                  <td>
                    <Badge tone={purchasingTone(r.status)}>{t(`purchasing.requestStatus.${r.status}`)}</Badge>
                  </td>
                  <td className="pur-table__num"><Bdi>{formatMinor(r.subtotal_minor, r.currency)}</Bdi></td>
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
                (id) => submitRequest(id),
                t(submittable.length === 1 ? "purchasing.toast.bulkReqSubmittedOne" : "purchasing.toast.bulkReqSubmitted", { count: submittable.length }),
              )
            }
          >
            {t("purchasing.requests.submit")}
          </button>
        )}
        {approvable.length > 0 && (
          <button
            className="btn btn--sm"
            onClick={() =>
              bulkAct(
                approvable,
                "approved",
                (id) => approveRequest(id),
                t(approvable.length === 1 ? "purchasing.toast.bulkReqApprovedOne" : "purchasing.toast.bulkReqApproved", { count: approvable.length }),
              )
            }
          >
            {t("purchasing.requests.approve")}
          </button>
        )}
      </BulkActionBar>
    </section>
  );
}
