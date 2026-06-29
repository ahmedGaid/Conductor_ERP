import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { getStockCount, postStockCount, setCountLine, type StockCount } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { EntityLink } from "../../components/EntityLink";
import { InventoryNav } from "./InventoryNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./inventory.css";

export function StockCountDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { id = "" } = useParams();
  const { data: count, loading, error, reload, mutate } = useAsync<StockCount>(
    () => getStockCount(id),
    [id],
    `inventory:count:${id}`,
  );

  const counting = count?.status === "counting";
  const posted = count?.status === "posted";

  // Optimistic line edit: reflect the typed count instantly, reconcile with the server's count.
  // No success toast — entering many counts in a row should stay quiet (visual restraint); only a
  // failure surfaces, with a rollback.
  function saveLine(lineId: string, value: string, current: string | null) {
    if (value === "" || value === current || !count) return;
    void runOptimistic<StockCount, StockCount>({
      current: count,
      mutate,
      optimistic: (c) => ({
        ...c,
        lines: (c.lines ?? []).map((ln) => (ln.id === lineId ? { ...ln, counted_quantity: value } : ln)),
      }),
      request: () => setCountLine(lineId, value),
      settle: (_predicted, updated) => updated,
      toast,
    });
  }

  // Optimistic post: flip to "posted" so the variance columns reveal immediately, then let the
  // server's count reconcile the authoritative variance figures. Failure rolls back to "counting".
  function onPost() {
    if (!count) return;
    void runOptimistic<StockCount, StockCount>({
      current: count,
      mutate,
      optimistic: (c) => ({ ...c, status: "posted" }),
      request: () => postStockCount(id),
      settle: (_predicted, updated) => updated,
      toast,
      success: t("inventory.toast.countPosted"),
    });
  }

  return (
    <section className="inv-page">
      <InventoryNav />
      <Link className="inv-link" to="/inventory/counts">← {t("inventory.counts.backToList")}</Link>

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {count && (
        <>
          <div className="inv-detail-head">
            <h2><EntityLink type="warehouse" value={count.warehouse_code} /> · <Bdi>{count.count_date}</Bdi></h2>
            <div className="inv-toolbar">
              <span className={`pill pill--${posted ? "completed" : count.status === "cancelled" ? "failed" : "running"}`}>
                {t(`inventory.counts.statuses.${count.status}`)}
              </span>
              {counting && (
                <button className="btn btn--primary" onClick={onPost}>
                  {t("inventory.counts.post")}
                </button>
              )}
            </div>
          </div>
          {counting && <p className="muted" style={{ fontSize: "var(--font-size-sm)" }}>{t("inventory.counts.enterHint")}</p>}

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
                    <td><EntityLink type="item" value={ln.item_sku} /> · {ln.item_name}</td>
                    <td className="inv-table__num"><Bdi>{ln.system_quantity}</Bdi></td>
                    <td className="inv-table__num">
                      {counting ? (
                        <input
                          className="latin inv-count-input"
                          inputMode="decimal"
                          defaultValue={ln.counted_quantity ?? ""}
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
