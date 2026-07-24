import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { NavIcon } from "../../app/icons";
import { getPurchaseOrder, updatePOLines, type NewPOLine, type PurchaseOrder } from "../../api/purchasing";
import { listItems } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { useDraftRecovery } from "../../hooks/useDraftRecovery";
import { useFormKeys } from "../../hooks/useFormKeys";
import { useToast } from "../../app/ToastContext";
import { formatMinor, minorToAmount, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ComboBox } from "../../components/ComboBox";
import { DraftRecoveryBanner } from "../../components/DraftRecoveryBanner";
import { DraftStatusIndicator } from "../../components/DraftStatusIndicator";
import { ErrorState } from "../../components/ErrorState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { EmptyState } from "../../components/EmptyState";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

interface DraftLine {
  item_sku: string;
  quantity: string;
  unit_cost: string;
}

const emptyLine = (): DraftLine => ({ item_sku: "", quantity: "", unit_cost: "" });

interface LinesDraft {
  lines: DraftLine[];
}

function draftFrom(order: PurchaseOrder | null): LinesDraft {
  if (!order || order.lines.length === 0) return { lines: [emptyLine()] };
  return {
    lines: order.lines.map((l) => ({
      item_sku: l.item_sku, quantity: l.quantity, unit_cost: minorToAmount(l.unit_cost_minor),
    })),
  };
}

// Edit-record path for a draft purchase order — replaces the lines only. Supplier/warehouse/tax
// were set at creation and aren't editable here (service contract is lines-only).
export function EditPurchaseOrderPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { id = "" } = useParams();
  const { data: order, loading, error, reload } = useAsync(() => getPurchaseOrder(id), [id], `purchasing:order:${id}`);
  const { data: items } = useAsync(listItems, [], "inventory:items");

  const [lines, setLines] = useState<DraftLine[]>([emptyLine()]);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const loadedRef = useRef(false);
  useEffect(() => {
    if (!order || loadedRef.current) return;
    loadedRef.current = true;
    setLines(draftFrom(order).lines);
  }, [order]);

  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef, onCancel: () => navigate(`/purchasing/orders/${id}`) });

  const baseline = useMemo(() => draftFrom(order), [order]);
  const draft = useMemo<LinesDraft>(() => ({ lines }), [lines]);
  const recovery = useDraftRecovery<LinesDraft>({
    workflowKey: "purchasing.order.edit",
    entityType: "purchase_order",
    relatedEntityId: id,
    value: draft,
    baseline,
    schemaVersion: 1,
    enabled: !!order,
  });

  function applyDraft(d: LinesDraft) {
    setLines(d.lines?.length ? d.lines : [emptyLine()]);
  }

  function setLine(i: number, patch: Partial<DraftLine>) {
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  const subtotal = lines.reduce((s, l) => {
    const qty = Number(l.quantity) || 0;
    const cost = parseToMinor(l.unit_cost) ?? 0;
    return s + Math.round(qty * cost);
  }, 0);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const payloadLines: NewPOLine[] = [];
    for (const l of lines) {
      const cost = parseToMinor(l.unit_cost);
      if (!l.item_sku || !l.quantity) continue;
      if (cost === null) {
        setFormError(t("purchasing.newOrder.badCost"));
        return;
      }
      payloadLines.push({ item_sku: l.item_sku, quantity: l.quantity, unit_cost: cost });
    }
    if (payloadLines.length === 0) {
      setFormError(t("purchasing.newOrder.needLine"));
      return;
    }
    setBusy(true);
    try {
      await updatePOLines(id, payloadLines);
      void recovery.complete(id);
      navigate(`/purchasing/orders/${id}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setBusy(false);
    }
  }

  const stockItems = (items ?? []).filter((i) => i.type === "stock");

  if (loading) return <section className="pur-page"><PurchasingNav /><ListSkeleton /></section>;
  if (error) return <section className="pur-page"><PurchasingNav /><ErrorState message={error} onRetry={reload} /></section>;
  if (order && order.status !== "draft") {
    return (
      <section className="pur-page">
        <PurchasingNav />
        <EmptyState title={t("purchasing.edit.notDraft")} hint={t("purchasing.edit.notDraftHint")} />
      </section>
    );
  }

  return (
    <section className="pur-page">
      <PurchasingNav />

      {recovery.recoverable && (
        <DraftRecoveryBanner
          entityLabel={t("drafts.workflow.purchasing.order.edit")}
          lastActiveAt={recovery.recoverable.lastActiveAt}
          onContinue={() => {
            const payload = recovery.recover();
            if (payload) applyDraft(payload);
          }}
          onDiscard={() => void recovery.discard()}
        />
      )}

      {order && (
        <form ref={formRef} className="card pur-page" onSubmit={onSubmit}>
          <div className="pur-toolbar">
            <label className="pur-field">
              <span>{t("purchasing.orders.supplier")}</span>
              <span className="latin muted">{order.supplier_code} · {order.supplier_name}</span>
            </label>
            <label className="pur-field">
              <span>{t("inventory.warehouse.label")}</span>
              <span className="latin muted">{order.warehouse_code}</span>
            </label>
          </div>

          <div className="pur-table-wrap">
            <table className="pur-table">
              <thead>
                <tr>
                  <th>{t("sales.newOrder.item")}</th>
                  <th className="pur-table__num">{t("inventory.onHand.quantity")}</th>
                  <th className="pur-table__num">{t("purchasing.newOrder.unitCost")}</th>
                  <th className="pur-table__num">{t("sales.orders.total")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {lines.map((l, i) => {
                  const lineTotal = Math.round((Number(l.quantity) || 0) * (parseToMinor(l.unit_cost) ?? 0));
                  return (
                    <tr key={i}>
                      <td>
                        <ComboBox
                          value={l.item_sku}
                          onChange={(v) => setLine(i, { item_sku: v })}
                          placeholder={t("common.selectField", { field: t("sales.newOrder.item") })}
                          options={stockItems.map((it) => ({ value: it.sku, label: `${it.sku} · ${it.name}` }))}
                        />
                      </td>
                      <td className="pur-table__num">
                        <input className="latin" inputMode="decimal" value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} />
                      </td>
                      <td className="pur-table__num">
                        <input className="latin" inputMode="decimal" value={l.unit_cost} onChange={(e) => setLine(i, { unit_cost: e.target.value })} placeholder="0.00" />
                      </td>
                      <td className="pur-table__num"><Bdi>{formatMinor(lineTotal)}</Bdi></td>
                      <td>
                        <button type="button" className="btn btn--sm btn--icon" onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))} disabled={lines.length <= 1} aria-label={t("common.delete")}><NavIcon name="close" /></button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={3}>{t("sales.newOrder.subtotal")}</td>
                  <td className="pur-table__num"><Bdi>{formatMinor(subtotal)}</Bdi></td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>

          <div className="pur-actions">
            <button type="button" className="btn btn--sm" onClick={() => setLines((ls) => [...ls, emptyLine()])}>
              {t("purchasing.newOrder.addLine")}
            </button>
            <button type="button" className="btn btn--sm btn--ghost" onClick={() => navigate(`/purchasing/orders/${id}`)}>
              {t("common.cancel")}
            </button>
            <button type="submit" className="btn btn--primary" disabled={busy}>
              {t("common.save")}
            </button>
            {recovery.conflict && <p className="muted" role="status">{t("drafts.conflict")}</p>}
            <DraftStatusIndicator status={recovery.status} savedAt={recovery.savedAt} />
          </div>
          {formError && <p className="error-text">{formError}</p>}
        </form>
      )}
    </section>
  );
}
