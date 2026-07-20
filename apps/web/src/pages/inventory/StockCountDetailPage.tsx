import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { BackLink } from "../../components/BackLink";
import { useSetPageActions } from "../../app/PageActionsContext";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { DocumentPrimaryButton } from "../../components/DocumentHeader";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { copyShareLink, printDocument } from "../../lib/documentActions";

import { getStockCount, postStockCount, setCountLine, type StockCount } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { Badge } from "../../components/Badge";
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

  // Live preview of the quantity variance while still counting — the server's own
  // variance_quantity/variance_value_minor stay 0 until post_count() runs, so showing THOSE fields
  // pre-post would silently lie. This is computed client-side from what's already on screen
  // (system vs counted), so it can't include the money value (unit cost isn't in this payload) —
  // shown once posting supplies the authoritative figure.
  function previewVariance(counted: string | null, system: string): number | null {
    if (counted == null || counted === "") return null;
    return Number(counted) - Number(system);
  }

  useSetDocumentCrumb(count ? `${count.warehouse_code} · ${count.count_date}` : undefined);

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

  // Bar primary = post the count (only while counting), exactly the old in-page button's gating.
  const barPrimary = useMemo(() => {
    if (!count || count.status !== "counting") return undefined;
    return <DocumentPrimaryButton action={{ label: t("inventory.counts.post"), onClick: onPost }} />;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [count, t]);
  const barMenu = useMemo<DocMenuItem[]>(() => {
    if (!count) return [];
    return [
      { key: "print", label: t("document.print"), icon: "print", onClick: () => printDocument(`${count.warehouse_code} ${count.count_date}`) },
      { key: "pdf", label: t("document.exportPdf"), icon: "download", onClick: () => printDocument(`${count.warehouse_code} ${count.count_date}`) },
      {
        key: "share",
        label: t("document.share"),
        icon: "share",
        onClick: () =>
          void copyShareLink(`/inventory/counts/${id}`).then((ok) =>
            toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
          ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [count, t]);
  useSetPageActions({ primary: barPrimary, menuItems: barMenu });

  return (
    <section className="inv-page">
      <InventoryNav />
      <BackLink to="/inventory/counts">{t("inventory.counts.backToList")}</BackLink>

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {count && (
        <>
          <div className="inv-detail-head">
            <h2><EntityLink type="warehouse" value={count.warehouse_code} /> · <Bdi>{count.count_date}</Bdi></h2>
            <div className="inv-toolbar">
              <Badge tone={posted ? "completed" : count.status === "cancelled" ? "failed" : "running"}>
                {t(`inventory.counts.statuses.${count.status}`)}
              </Badge>
            </div>
          </div>
          {counting && <p className="hint">{t("inventory.counts.enterHint")}</p>}

          <div className="card inv-table-wrap">
            <table className="inv-table">
              <thead>
                <tr>
                  <th>{t("inventory.counts.item")}</th>
                  <th className="inv-table__num">{t("inventory.counts.system")}</th>
                  <th className="inv-table__num">{t("inventory.counts.counted")}</th>
                  <th className="inv-table__num">{t("inventory.counts.variance")}</th>
                  {posted && <th className="inv-table__num">{t("inventory.counts.varianceValue")}</th>}
                </tr>
              </thead>
              <tbody>
                {(count.lines ?? []).map((ln) => {
                  const variance = posted ? Number(ln.variance_quantity) : previewVariance(ln.counted_quantity, ln.system_quantity);
                  return (
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
                    <td className={`inv-table__num ${variance === null || variance === 0 ? "" : variance < 0 ? "inv-warn" : "inv-ok"}`}>
                      <Bdi>{variance === null ? "—" : variance}</Bdi>
                    </td>
                    {posted && (
                      <td className="inv-table__num"><Bdi>{formatMinor(ln.variance_value_minor)}</Bdi></td>
                    )}
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
