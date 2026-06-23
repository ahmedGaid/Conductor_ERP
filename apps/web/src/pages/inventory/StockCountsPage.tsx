import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { createStockCount, getStockCount, listStockCounts, listWarehouses, type CountStatus } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useToast } from "../../app/ToastContext";
import { prefetch } from "../../lib/prefetch";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

const COUNT_STATUSES: CountStatus[] = ["counting", "posted", "cancelled"];
type StockCount = Awaited<ReturnType<typeof listStockCounts>>[number];

export function StockCountsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(listStockCounts, [], "inventory:counts");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<StockCount>[]>(
    () => [
      { key: "warehouse", label: t("inventory.counts.warehouse"), type: "text", accessor: (c) => c.warehouse_code },
      { key: "date", label: t("inventory.counts.date"), type: "date", accessor: (c) => c.count_date },
      {
        key: "status",
        label: t("inventory.counts.status"),
        type: "select",
        options: COUNT_STATUSES.map((s) => ({ value: s, label: t(`inventory.counts.statuses.${s}`) })),
        accessor: (c) => c.status,
      },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((c) => matchesAllFilters(c, fields, filters)) : data),
    [data, fields, filters],
  );

  const statusTabs = useMemo(
    () => COUNT_STATUSES.map((s) => ({ value: s, label: t(`inventory.counts.statuses.${s}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((c) => c.status === tab)) : filtered),
    [filtered, tab],
  );

  // j/k move a row highlight, Enter/o opens it on the detail page.
  const { active } = useListKeyboardNav<StockCount>({
    items: visible ?? [],
    onOpen: (c) => navigate(`/inventory/counts/${c.id}`),
  });

  const [warehouse, setWarehouse] = useState("");
  const [countDate, setCountDate] = useState(today());
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!warehouse) {
      setFormError(t("inventory.counts.pickWarehouse"));
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      const count = await createStockCount({ warehouse_code: warehouse, count_date: countDate });
      reload();
      toast.show(t("inventory.toast.countStarted"), "success");
      navigate(`/inventory/counts/${count.id}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="inv-page">
      <InventoryNav />

      <form className="card inv-toolbar" onSubmit={onSubmit}>
        <label className="inv-field">
          <span>{t("inventory.counts.warehouse")}</span>
          <select className="latin" value={warehouse} onChange={(e) => setWarehouse(e.target.value)} required>
            <option value="">—</option>
            {(warehouses ?? []).filter((w) => w.is_active).map((w) => (
              <option key={w.code} value={w.code}>{w.code} · {w.name}</option>
            ))}
          </select>
        </label>
        <label className="inv-field">
          <span>{t("inventory.counts.date")}</span>
          <input className="latin" type="date" value={countDate} onChange={(e) => setCountDate(e.target.value)} required />
        </label>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {t("inventory.counts.start")}
        </button>
      </form>
      <p className="muted" style={{ fontSize: "var(--font-size-sm)" }}>{t("inventory.counts.startHint")}</p>
      {formError && <p className="error-text">{formError}</p>}

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}

      {data && data.length === 0 && (
        <EmptyState title={t("inventory.counts.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="inv-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={statusTabs}
          accessor={(c) => c.status}
          value={tab}
          onChange={setTab}
          ariaLabel={t("inventory.counts.status")}
        />
      )}
      {data && data.length > 0 && visible && visible.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {visible && visible.length > 0 && (
        <div className="card inv-table-wrap">
          <table className="inv-table">
            <thead>
              <tr>
                <th>{t("inventory.counts.warehouse")}</th>
                <th>{t("inventory.counts.date")}</th>
                <th className="inv-table__num">{t("inventory.counts.lines")}</th>
                <th>{t("inventory.counts.status")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((c, i) => (
                <tr key={c.id} data-kbd-active={i === active ? "true" : undefined} aria-selected={i === active}>
                  <td>
                    <Link
                      className="inv-link"
                      to={`/inventory/counts/${c.id}`}
                      onMouseEnter={() => prefetch(`inventory:count:${c.id}`, () => getStockCount(c.id))}
                      onFocus={() => prefetch(`inventory:count:${c.id}`, () => getStockCount(c.id))}
                    >
                      <Bdi>{c.warehouse_code}</Bdi>
                    </Link>
                  </td>
                  <td><Bdi>{c.count_date}</Bdi></td>
                  <td className="inv-table__num"><Bdi>{c.line_count}</Bdi></td>
                  <td>
                    <span className={`pill pill--${c.status === "posted" ? "completed" : c.status === "cancelled" ? "failed" : "running"}`}>
                      {t(`inventory.counts.statuses.${c.status}`)}
                    </span>
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
