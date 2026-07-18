import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { getItem } from "../../api/inventory";
import { listCustomFieldDefs } from "../../api/customFields";
import { formatCustomFieldValue } from "../../lib/customFields";
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
import { Disclosure } from "../../components/Disclosure";
import { EntityLink } from "../../components/EntityLink";
import { RecordTimeline } from "../../components/RecordTimelineLazy";
import { InventoryNav } from "./InventoryNav";
import { MovementsTable } from "./MovementsTable";
import "./inventory.css";

export function ItemDetailPage() {
  const { t, i18n } = useTranslation();
  const isArabic = i18n.resolvedLanguage?.startsWith("ar") ?? true;
  const { sku = "" } = useParams();
  const { data, loading, error, reload } = useAsync(() => getItem(sku), [sku], `inventory:item:${sku}`);
  const { data: customFieldDefs } = useAsync(
    () => listCustomFieldDefs("inventory.item"),
    [],
    "settings:customFields:inventory.item",
  );
  const toast = useToast();

  useSetDocumentCrumb(data?.item.sku);

  // A master-data record — no lifecycle primary; the ⋯ menu carries print / export / share.
  const barMenu = useMemo<DocMenuItem[]>(() => {
    if (!data) return [];
    return [
      { key: "print", label: t("document.print"), icon: "print", onClick: () => printDocument(data.item.sku) },
      { key: "pdf", label: t("document.exportPdf"), icon: "download", onClick: () => printDocument(data.item.sku) },
      {
        key: "share",
        label: t("document.share"),
        icon: "share",
        onClick: () =>
          void copyShareLink(`/inventory/items/${sku}`).then((ok) =>
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
      <Link className="inv-back" to="/inventory/items">{t("inventory.detail.backToItems")}</Link>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <>
          <div className="card inv-detail__head">
            <h2 className="latin inv-detail__title"><Bdi>{data.item.sku}</Bdi></h2>
            <p className="inv-detail__name">{data.item.name}</p>
            <dl className="inv-detail__facts">
              <div className="inv-detail__fact">
                <dt>{t("inventory.item.uom")}</dt>
                <dd>{data.item.uom}</dd>
              </div>
              <div className="inv-detail__fact">
                <dt>{t("inventory.item.type")}</dt>
                <dd>{t(`inventory.types.${data.item.type}`)}</dd>
              </div>
              {data.item.category_code && (
                <div className="inv-detail__fact">
                  <dt>{t("inventory.item.category")}</dt>
                  <dd className="latin">{data.item.category_code}</dd>
                </div>
              )}
              <div className="inv-detail__fact">
                <dt>{t("inventory.detail.onHandValue")}</dt>
                <dd><Bdi>{formatMinor(data.stock.total_value_minor)}</Bdi></dd>
              </div>
              {(customFieldDefs ?? []).map((def) => {
                const value = formatCustomFieldValue(def, data.item.custom_data?.[def.key]);
                if (!value) return null;
                return (
                  <div className="inv-detail__fact" key={def.key}>
                    <dt>{isArabic ? def.label_ar : def.label_en}</dt>
                    <dd>{value}</dd>
                  </div>
                );
              })}
            </dl>
          </div>

          <h3 className="inv-section-title">{t("inventory.detail.stockByWarehouse")}</h3>
          {data.stock.rows.length > 0 ? (
            <div className="card inv-table-wrap">
              <table className="inv-table">
                <thead>
                  <tr>
                    <th>{t("inventory.warehouse.code")}</th>
                    <th className="inv-table__num">{t("inventory.onHand.quantity")}</th>
                    <th className="inv-table__num">{t("inventory.onHand.avgCost")}</th>
                    <th className="inv-table__num">{t("inventory.onHand.value")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.stock.rows.map((r) => (
                    <tr key={r.warehouse_code}>
                      <td><EntityLink type="warehouse" value={r.warehouse_code} /></td>
                      <td className="inv-table__num"><Bdi>{r.quantity}</Bdi></td>
                      <td className="inv-table__num"><Bdi>{formatMinor(r.avg_cost_minor)}</Bdi></td>
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
          <MovementsTable movements={data.movements} show="item" />

          <Disclosure summary={t("timeline.title")}>
            <RecordTimeline entityType="Item" entityId={data.item.sku} />
          </Disclosure>
        </>
      )}
    </section>
  );
}
