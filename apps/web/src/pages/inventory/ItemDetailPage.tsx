import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { getItem, suggestItemEtaCode, updateItem, updateItemEtaCoding, type EtaCodeStatus, type Item } from "../../api/inventory";
import { listCustomFieldDefs } from "../../api/customFields";
import { formatCustomFieldValue } from "../../lib/customFields";
import { useAsync } from "../../hooks/useAsync";
import { useDraftRecovery } from "../../hooks/useDraftRecovery";
import { runOptimistic } from "../../lib/optimistic";
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
import { DraftRecoveryBanner } from "../../components/DraftRecoveryBanner";
import { DraftStatusIndicator } from "../../components/DraftStatusIndicator";
import { EntityLink } from "../../components/EntityLink";
import { RecordTimeline } from "../../components/RecordTimelineLazy";
import { InventoryNav } from "./InventoryNav";
import { MovementsTable } from "./MovementsTable";
import "./inventory.css";

interface ItemEditDraft {
  name: string;
  uom: string;
  reorderPoint: string;
  isActive: boolean;
}

function itemDraftFrom(item: Item | null): ItemEditDraft {
  return {
    name: item?.name ?? "", uom: item?.uom ?? "unit",
    reorderPoint: item?.reorder_point ?? "0", isActive: item?.is_active ?? true,
  };
}

export function ItemDetailPage() {
  const { t, i18n } = useTranslation();
  const isArabic = i18n.resolvedLanguage?.startsWith("ar") ?? true;
  const { sku = "" } = useParams();
  const { data, loading, error, reload, mutate } = useAsync(() => getItem(sku), [sku], `inventory:item:${sku}`);
  const { data: customFieldDefs } = useAsync(
    () => listCustomFieldDefs("inventory.item"),
    [],
    "settings:customFields:inventory.item",
  );
  const toast = useToast();

  // Local edit state for the ETA product-identity fields (FILE_06) — synced from the loaded item,
  // then edited freely until Save.
  const [gpcCode, setGpcCode] = useState("");
  const [etaItemCode, setEtaItemCode] = useState("");
  const [etaCodeStatus, setEtaCodeStatus] = useState<EtaCodeStatus>("not_submitted");
  const [savingCoding, setSavingCoding] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  useEffect(() => {
    if (!data) return;
    setGpcCode(data.item.gpc_code);
    setEtaItemCode(data.item.eta_item_code);
    setEtaCodeStatus(data.item.eta_code_status);
  }, [data?.item.sku, data?.item.gpc_code, data?.item.eta_item_code, data?.item.eta_code_status]);

  // Edit form — name/uom/reorder point/active. sku and type are immutable (see ItemUpdateSerializer).
  const [editName, setEditName] = useState("");
  const [editUom, setEditUom] = useState("unit");
  const [editReorder, setEditReorder] = useState("0");
  const [editActive, setEditActive] = useState(true);
  const [savingEdit, setSavingEdit] = useState(false);
  useEffect(() => {
    if (!data) return;
    setEditName(data.item.name);
    setEditUom(data.item.uom);
    setEditReorder(data.item.reorder_point);
    setEditActive(data.item.is_active);
  }, [data?.item.sku]);

  const item = data?.item ?? null;
  const editBaseline = useMemo(() => itemDraftFrom(item), [item]);
  const editDraft = useMemo<ItemEditDraft>(
    () => ({ name: editName, uom: editUom, reorderPoint: editReorder, isActive: editActive }),
    [editName, editUom, editReorder, editActive],
  );
  const editRecovery = useDraftRecovery<ItemEditDraft>({
    workflowKey: "inventory.item.edit",
    entityType: "item",
    relatedEntityId: sku,
    value: editDraft,
    baseline: editBaseline,
    schemaVersion: 1,
    enabled: !!item,
  });

  function applyEditDraft(d: ItemEditDraft) {
    setEditName(d.name ?? "");
    setEditUom(d.uom ?? "unit");
    setEditReorder(d.reorderPoint ?? "0");
    setEditActive(d.isActive ?? true);
  }

  async function onSaveEdit() {
    if (!data) return;
    setSavingEdit(true);
    const payload = { name: editName.trim(), uom: editUom.trim() || "unit", reorder_point: editReorder, is_active: editActive };
    await runOptimistic({
      current: data,
      mutate,
      optimistic: (cur) => ({ ...cur, item: { ...cur.item, ...payload } }),
      request: () => updateItem(sku, payload),
      settle: (predicted, updated) => ({ ...predicted, item: updated }),
      toast,
      success: t("common.saved"),
    });
    void editRecovery.complete(sku);
    setSavingEdit(false);
  }

  async function onSaveCoding() {
    if (!data) return;
    setSavingCoding(true);
    const payload = { gpc_code: gpcCode.trim(), eta_item_code: etaItemCode.trim(), eta_code_status: etaCodeStatus };
    await runOptimistic({
      current: data,
      mutate,
      optimistic: (cur) => ({ ...cur, item: { ...cur.item, ...payload } }),
      request: () => updateItemEtaCoding(sku, payload),
      settle: (predicted, updated) => ({ ...predicted, item: updated }),
      toast,
      success: t("inventory.eta.saved"),
    });
    setSavingCoding(false);
  }

  async function onSuggestCode() {
    setSuggesting(true);
    try {
      const { suggestion, missing } = await suggestItemEtaCode(sku);
      if (missing.length > 0) {
        const label = missing.map((m) => t(`inventory.eta.missing.${m}`)).join(t("inventory.eta.missingJoin"));
        toast.show(t("inventory.eta.missingForSuggestion", { fields: label }), "error");
      } else {
        setEtaItemCode(suggestion);
      }
    } catch (e) {
      toast.show(e instanceof Error ? e.message : String(e), "error");
    }
    setSuggesting(false);
  }

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

          {editRecovery.recoverable && (
            <DraftRecoveryBanner
              entityLabel={t("drafts.workflow.inventory.item.edit")}
              lastActiveAt={editRecovery.recoverable.lastActiveAt}
              onContinue={() => {
                const payload = editRecovery.recover();
                if (payload) applyEditDraft(payload);
              }}
              onDiscard={() => void editRecovery.discard()}
            />
          )}
          <Disclosure summary={t("inventory.detail.editItem")}>
            <div className="card inv-toolbar">
              <label className="inv-field">
                <span>{t("sales.customer.name")}</span>
                <input value={editName} onChange={(e) => setEditName(e.target.value)} />
              </label>
              <label className="inv-field">
                <span>{t("inventory.item.uom")}</span>
                <input className="latin" value={editUom} onChange={(e) => setEditUom(e.target.value)} />
              </label>
              <label className="inv-field">
                <span>{t("inventory.item.reorderPoint")}</span>
                <input className="latin" inputMode="decimal" value={editReorder} onChange={(e) => setEditReorder(e.target.value)} />
              </label>
              <label className="inv-field inv-field--check">
                <input type="checkbox" checked={editActive} onChange={(e) => setEditActive(e.target.checked)} />
                <span>{t("inventory.item.active")}</span>
              </label>
              {editRecovery.conflict && <p className="muted" role="status">{t("drafts.conflict")}</p>}
              <DraftStatusIndicator status={editRecovery.status} savedAt={editRecovery.savedAt} />
              <button className="btn btn--sm btn--primary" type="button" onClick={() => void onSaveEdit()} disabled={savingEdit}>
                {t("common.save")}
              </button>
            </div>
          </Disclosure>

          <Disclosure summary={t("inventory.eta.title")}>
            <p className="muted">{t("inventory.eta.hint")}</p>
            <div className="card inv-toolbar">
              <label className="inv-field">
                <span>{t("inventory.eta.gpcCode")}</span>
                <input className="latin" value={gpcCode} onChange={(e) => setGpcCode(e.target.value)} />
              </label>
              <label className="inv-field">
                <span>{t("inventory.eta.itemCode")}</span>
                <input className="latin" value={etaItemCode} onChange={(e) => setEtaItemCode(e.target.value)} />
              </label>
              <button className="btn btn--sm btn--ghost" type="button" onClick={onSuggestCode} disabled={suggesting}>
                {t("inventory.eta.suggest")}
              </button>
              <label className="inv-field">
                <span>{t("inventory.eta.status")}</span>
                <select value={etaCodeStatus} onChange={(e) => setEtaCodeStatus(e.target.value as EtaCodeStatus)}>
                  <option value="not_submitted">{t("inventory.eta.statusValues.not_submitted")}</option>
                  <option value="pending">{t("inventory.eta.statusValues.pending")}</option>
                  <option value="accepted">{t("inventory.eta.statusValues.accepted")}</option>
                  <option value="rejected">{t("inventory.eta.statusValues.rejected")}</option>
                </select>
              </label>
              <button className="btn btn--sm btn--primary" type="button" onClick={onSaveCoding} disabled={savingCoding}>
                {t("inventory.eta.save")}
              </button>
            </div>
          </Disclosure>

          <Disclosure summary={t("timeline.title")}>
            <RecordTimeline entityType="Item" entityId={data.item.sku} />
          </Disclosure>
        </>
      )}
    </section>
  );
}
