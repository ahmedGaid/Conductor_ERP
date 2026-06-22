import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { listRequests, type PurchaseRequest } from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

const PR_STATUSES = ["draft", "submitted", "approved", "rejected", "converted", "cancelled"] as const;

export function PurchaseRequestsPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(() => listRequests(), [], "purchasing:requests");
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
                <th>{t("purchasing.requests.number")}</th>
                <th>{t("purchasing.orders.supplier")}</th>
                <th>{t("common.date")}</th>
                <th>{t("common.status")}</th>
                <th className="pur-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link to={`/purchasing/requests/${r.id}`} className="latin">{r.number}</Link>
                  </td>
                  <td>{r.supplier_name}</td>
                  <td className="latin muted">{r.request_date}</td>
                  <td>
                    <span className={`pur-badge pur-badge--${r.status}`}>
                      {t(`purchasing.requestStatus.${r.status}`)}
                    </span>
                  </td>
                  <td className="pur-table__num"><Bdi>{formatMinor(r.subtotal_minor, r.currency)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
