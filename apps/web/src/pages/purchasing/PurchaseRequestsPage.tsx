import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { listRequests, getRequest, submitRequest, approveRequest, type PurchaseRequest } from "../../api/purchasing";
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
import { StatusRing } from "../../components/StatusRing";
import { purchasingTone } from "../../lib/statusTone";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
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
  const savedViews = useSavedViews({ listKey: "purchasing:requests", fields, filters, setFilters });

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

  const csvColumns = useMemo<CsvColumn<PurchaseRequest>[]>(
    () => [
      { header: t("purchasing.requests.number"), accessor: (r) => r.number },
      { header: t("purchasing.orders.supplier"), accessor: (r) => r.supplier_name },
      { header: t("common.date"), accessor: (r) => r.request_date },
      { header: t("common.status"), accessor: (r) => t(`purchasing.requestStatus.${r.status}`) },
      { header: t("sales.orders.total"), accessor: (r) => formatMinor(r.subtotal_minor, r.currency) },
    ],
    [t],
  );
  const listPrimary = useMemo(
    () => ({ label: t("purchasing.tabs.newRequest"), onClick: () => navigate("/purchasing/requests/new") }),
    [t, navigate],
  );
  useListPageActions({ primary: listPrimary, rows: visible, columns: csvColumns, filename: "purchase-requests" });

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
        <EmptyState
          title={t("filter.noMatch")}
          hint={t("filter.noMatchHint")}
          action={{ label: t("filter.clearAll"), onClick: () => setFilters([]) }}
        />
      )}

      {visible && visible.length > 0 && (
        <div className="card pur-table-wrap">
          <table className="pur-table">
            <thead>
              <tr>
                <SelectAllCell
                  className="pur-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
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
                  <SelectRowCell
                    className="pur-table__select"
                    checked={selection.isSelected(r.id)}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
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
                    <StatusRing
                      docType="purchaseRequest"
                      status={r.status}
                      tone={purchasingTone(r.status)}
                      label={t(`purchasing.requestStatus.${r.status}`)}
                    />
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
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("purchase-requests-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
