import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { getWarehouse } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { useSetPageActions } from "../../app/PageActionsContext";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { copyShareLink, printDocument } from "../../lib/documentActions";
import { ErrorState } from "../../components/ErrorState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { EntityLink } from "../../components/EntityLink";
import { InventoryNav } from "./InventoryNav";
import { MovementsTable } from "./MovementsTable";
import "./inventory.css";

export function WarehouseDetailPage() {
  const { t } = useTranslation();
  const { code = "" } = useParams();
  const { data, loading, error, reload } = useAsync(
    () => getWarehouse(code),
    [code],
    `inventory:warehouse:${code}`,
  );
  const toast = useToast();

  useSetDocumentCrumb(data?.warehouse.code);

  // A master-data record — no lifecycle primary; the ⋯ menu carries print / export / share.
  const barMenu = useMemo<DocMenuItem[]>(() => {
    if (!data) return [];
    return [
      { key: "print", label: t("document.print"), icon: "print", onClick: () => printDocument(data.warehouse.code) },
      { key: "pdf", label: t("document.exportPdf"), icon: "download", onClick: () => printDocument(data.warehouse.code) },
      {
        key: "share",
        label: t("document.share"),
        icon: "share",
        onClick: () =>
          void copyShareLink(`/inventory/warehouses/${code}`).then((ok) =>
            toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
          ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, t]);
  useSetPageActions({ menuItems: barMenu });

  return (
    <section className="inv-page">
      <InventoryNav />
      <Link className="inv-back" to="/inventory/warehouses">{t("inventory.detail.backToWarehouses")}</Link>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <>
          <div className="card inv-detail__head">
            <h2 className="latin inv-detail__title"><Bdi>{data.warehouse.code}</Bdi></h2>
            <p className="inv-detail__name">{data.warehouse.name}</p>
            <dl className="inv-detail__facts">
              <div className="inv-detail__fact">
                <dt>{t("inventory.detail.status")}</dt>
                <dd>{data.warehouse.is_active ? t("inventory.detail.active") : t("inventory.detail.inactive")}</dd>
              </div>
              <div className="inv-detail__fact">
                <dt>{t("inventory.detail.onHandValue")}</dt>
                <dd><Bdi>{formatMinor(data.stock.total_value_minor)}</Bdi></dd>
              </div>
            </dl>
          </div>

          <h3 className="inv-section-title">{t("inventory.detail.stockByItem")}</h3>
          {data.stock.rows.length > 0 ? (
            <div className="card inv-table-wrap">
              <table className="inv-table">
                <thead>
                  <tr>
                    <th>{t("inventory.item.sku")}</th>
                    <th>{t("inventory.item.name")}</th>
                    <th className="inv-table__num">{t("inventory.onHand.quantity")}</th>
                    <th className="inv-table__num">{t("inventory.onHand.value")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.stock.rows.map((r) => (
                    <tr key={r.sku}>
                      <td><EntityLink type="item" value={r.sku} /></td>
                      <td>{r.item_name}</td>
                      <td className="inv-table__num"><Bdi>{r.quantity}</Bdi></td>
                      <td className="inv-table__num"><Bdi>{formatMinor(r.value_minor)}</Bdi></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted inv-detail__empty">{t("inventory.detail.noStock")}</p>
          )}

          <h3 className="inv-section-title">{t("inventory.detail.movements")}</h3>
          <MovementsTable movements={data.movements} show="warehouse" />
        </>
      )}
    </section>
  );
}
