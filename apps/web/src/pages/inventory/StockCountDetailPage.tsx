import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { getStockCount, postStockCount, setCountLine } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

export function StockCountDetailPage() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const { data: count, loading, error, reload } = useAsync(() => getStockCount(id), [id]);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const counting = count?.status === "counting";
  const posted = count?.status === "posted";

  async function saveLine(lineId: string, value: string, current: string | null) {
    if (value === "" || value === current) return;
    setBusy(true);
    setActionError(null);
    try {
      await setCountLine(lineId, value);
      reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onPost() {
    setBusy(true);
    setActionError(null);
    try {
      await postStockCount(id);
      reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="inv-page">
      <h1>{t("nav.inventory")}</h1>
      <InventoryNav />
      <Link className="inv-link" to="/inventory/counts">← {t("inventory.counts.backToList")}</Link>

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}

      {count && (
        <>
          <div className="inv-detail-head">
            <h2><Bdi>{count.warehouse_code}</Bdi> · <Bdi>{count.count_date}</Bdi></h2>
            <div className="inv-toolbar">
              <span className={`pill pill--${posted ? "completed" : count.status === "cancelled" ? "failed" : "running"}`}>
                {t(`inventory.counts.statuses.${count.status}`)}
              </span>
              {counting && (
                <button className="btn btn--primary" disabled={busy} onClick={onPost}>
                  {t("inventory.counts.post")}
                </button>
              )}
            </div>
          </div>
          {counting && <p className="muted" style={{ fontSize: "var(--font-size-sm)" }}>{t("inventory.counts.enterHint")}</p>}
          {actionError && <p className="error-text">{actionError}</p>}

          <div className="card inv-table-wrap">
            <table className="inv-table">
              <thead>
                <tr>
                  <th>{t("inventory.counts.item")}</th>
                  <th className="inv-table__num">{t("inventory.counts.system")}</th>
                  <th className="inv-table__num">{t("inventory.counts.counted")}</th>
                  {posted && <th className="inv-table__num">{t("inventory.counts.variance")}</th>}
                  {posted && <th className="inv-table__num">{t("inventory.counts.varianceValue")}</th>}
                </tr>
              </thead>
              <tbody>
                {(count.lines ?? []).map((ln) => (
                  <tr key={ln.id}>
                    <td><Bdi>{ln.item_sku}</Bdi> · {ln.item_name}</td>
                    <td className="inv-table__num"><Bdi>{ln.system_quantity}</Bdi></td>
                    <td className="inv-table__num">
                      {counting ? (
                        <input
                          className="latin inv-count-input"
                          inputMode="decimal"
                          defaultValue={ln.counted_quantity ?? ""}
                          disabled={busy}
                          onBlur={(e) => saveLine(ln.id, e.target.value.trim(), ln.counted_quantity)}
                        />
                      ) : (
                        <Bdi>{ln.counted_quantity ?? "—"}</Bdi>
                      )}
                    </td>
                    {posted && (
                      <td className={`inv-table__num ${Number(ln.variance_quantity) === 0 ? "" : Number(ln.variance_quantity) < 0 ? "inv-warn" : "inv-ok"}`}>
                        <Bdi>{ln.variance_quantity}</Bdi>
                      </td>
                    )}
                    {posted && (
                      <td className="inv-table__num"><Bdi>{formatMinor(ln.variance_value_minor)}</Bdi></td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
