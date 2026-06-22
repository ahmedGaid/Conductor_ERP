import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  listETAInvoices,
  pollETAInvoice,
  submitETAInvoice,
  type ETAInvoice,
} from "../../api/einvoice";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { ExportButtons } from "../../components/ExportButtons";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { RowActions } from "../../components/RowActions";
import { EInvoiceNav } from "./EInvoiceNav";
import "./einvoice.css";

const EINVOICE_STATUSES = ["draft", "submitted", "valid", "rejected", "cancelled"] as const;

export function EInvoicesPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(() => listETAInvoices(), [], "einvoice:invoices");
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<ETAInvoice>[]>(
    () => [
      {
        key: "status",
        label: t("common.status"),
        type: "select",
        options: EINVOICE_STATUSES.map((s) => ({ value: s, label: t(`einvoice.status.${s}`) })),
        accessor: (e) => e.status,
      },
      { key: "customer", label: t("einvoice.customer"), type: "text", accessor: (e) => e.customer_name || e.customer_code },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((e) => matchesAllFilters(e, fields, filters)) : data),
    [data, fields, filters],
  );

  const statusTabs = useMemo(
    () => EINVOICE_STATUSES.map((s) => ({ value: s, label: t(`einvoice.status.${s}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((e) => e.status === tab)) : filtered),
    [filtered, tab],
  );

  async function run(id: string, fn: () => Promise<ETAInvoice>) {
    setBusy(id);
    setActionError(null);
    try {
      await fn();
      reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="ein-page">
      <EInvoiceNav />

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
      {actionError && <p className="error-text">{actionError}</p>}
      {data && data.length === 0 && <EmptyState title={t("einvoice.empty")} />}

      {data && data.length > 0 && (
        <div className="ein-toolbar">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
          <ExportButtons path="/einvoice/invoices" />
        </div>
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={statusTabs}
          accessor={(e) => e.status}
          value={tab}
          onChange={setTab}
          ariaLabel={t("common.status")}
        />
      )}
      {data && data.length > 0 && visible && visible.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {visible && visible.length > 0 && (
        <div className="card ein-table-wrap">
          <table className="ein-table">
            <thead>
              <tr>
                <th>{t("einvoice.invoice")}</th>
                <th>{t("einvoice.customer")}</th>
                <th className="ein-table__num">{t("einvoice.tax")}</th>
                <th className="ein-table__num">{t("einvoice.total")}</th>
                <th>{t("einvoice.uuid")}</th>
                <th>{t("einvoice.statusHeader")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {visible.map((e) => (
                <tr key={e.id}>
                  <td className="latin">{e.invoice_number}</td>
                  <td>{e.customer_name || e.customer_code}</td>
                  <td className="ein-table__num"><Bdi>{formatMinor(e.tax_minor, e.currency)}</Bdi></td>
                  <td className="ein-table__num"><Bdi>{formatMinor(e.total_minor, e.currency)}</Bdi></td>
                  <td className="latin muted">{e.uuid ? `${e.uuid.slice(0, 12)}…` : "—"}</td>
                  <td>
                    <span className={`ein-badge ein-badge--${e.status}`}>
                      {t(`einvoice.status.${e.status}`)}
                    </span>
                  </td>
                  <td>
                    <RowActions label={t("common.actions")}>
                      {e.status === "draft" && (
                        <button className="btn btn--sm" disabled={busy === e.id} onClick={() => run(e.id, () => submitETAInvoice(e.id))}>
                          {t("einvoice.submit")}
                        </button>
                      )}
                      {e.status === "submitted" && (
                        <button className="btn btn--sm" disabled={busy === e.id} onClick={() => run(e.id, () => pollETAInvoice(e.id))}>
                          {t("einvoice.poll")}
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
