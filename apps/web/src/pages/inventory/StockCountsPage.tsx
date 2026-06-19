import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { createStockCount, listStockCounts, listWarehouses } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function StockCountsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(listStockCounts, [], "inventory:counts");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");

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
      navigate(`/inventory/counts/${count.id}`);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
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
              {data.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link className="inv-link" to={`/inventory/counts/${c.id}`}><Bdi>{c.warehouse_code}</Bdi></Link>
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
