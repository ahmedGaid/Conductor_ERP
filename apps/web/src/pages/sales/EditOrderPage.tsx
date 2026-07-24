import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { NavIcon } from "../../app/icons";
import { getOrder, updateOrderLines, type NewOrderLine, type SalesOrder } from "../../api/sales";
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
import { SalesNav } from "./SalesNav";
import "./sales.css";

interface DraftLine {
  item_sku: string;
  quantity: string;
  unit_price: string;
  discount: string;
}

const emptyLine = (): DraftLine => ({ item_sku: "", quantity: "1", unit_price: "", discount: "" });

interface LinesDraft {
  lines: DraftLine[];
}

function draftFrom(order: SalesOrder | null): LinesDraft {
  if (!order || order.lines.length === 0) return { lines: [emptyLine()] };
  return {
    lines: order.lines.map((l) => ({
      item_sku: l.item_sku, quantity: l.quantity,
      unit_price: minorToAmount(l.unit_price_minor),
      discount: l.discount_minor ? minorToAmount(l.discount_minor) : "",
    })),
  };
}

// Edit-record path for a draft sales order — replaces the lines only. Customer/warehouse/tax were
// set at creation and aren't editable here (service contract is lines-only; see erp/sales/services).
export function EditOrderPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { id = "" } = useParams();
  const { data: order, loading, error, reload } = useAsync(() => getOrder(id), [id], `sales:order:${id}`);
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
  useFormKeys({ formRef, onCancel: () => navigate(`/sales/orders/${id}`) });

  const baseline = useMemo(() => draftFrom(order), [order]);
  const draft = useMemo<LinesDraft>(() => ({ lines }), [lines]);
  const recovery = useDraftRecovery<LinesDraft>({
    workflowKey: "sales.order.edit",
    entityType: "order",
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
    const price = parseToMinor(l.unit_price) ?? 0;
    const discount = parseToMinor(l.discount) ?? 0;
    return s + Math.round(qty * price) - discount;
  }, 0);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const payloadLines: NewOrderLine[] = [];
    for (const l of lines) {
      const price = parseToMinor(l.unit_price);
      if (!l.item_sku || !l.quantity) continue;
      if (price === null) {
        setFormError(t("sales.newOrder.badPrice"));
        return;
      }
      const discount = l.discount ? parseToMinor(l.discount) : 0;
      if (discount === null) {
        setFormError(t("sales.newOrder.badPrice"));
        return;
      }
      payloadLines.push({ item_sku: l.item_sku, quantity: l.quantity, unit_price: price, discount });
    }
    if (payloadLines.length === 0) {
      setFormError(t("sales.newOrder.needLine"));
      return;
    }
    setBusy(true);
    try {
      await updateOrderLines(id, payloadLines);
      void recovery.complete(id);
      navigate(`/sales/orders/${id}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setBusy(false);
    }
  }

  const stockItems = (items ?? []).filter((i) => i.type === "stock");

  if (loading) return <section className="sales-page"><SalesNav /><ListSkeleton /></section>;
  if (error) return <section className="sales-page"><SalesNav /><ErrorState message={error} onRetry={reload} /></section>;
  if (order && order.status !== "draft") {
    return (
      <section className="sales-page">
        <SalesNav />
        <EmptyState title={t("sales.edit.notDraft")} hint={t("sales.edit.notDraftHint")} />
      </section>
    );
  }

  return (
    <section className="sales-page">
      <SalesNav />

      {recovery.recoverable && (
        <DraftRecoveryBanner
          entityLabel={t("drafts.workflow.sales.order.edit")}
          lastActiveAt={recovery.recoverable.lastActiveAt}
          onContinue={() => {
            const payload = recovery.recover();
            if (payload) applyDraft(payload);
          }}
          onDiscard={() => void recovery.discard()}
        />
      )}

      {order && (
        <form ref={formRef} className="card sales-page" onSubmit={onSubmit}>
          <div className="sales-toolbar">
            <label className="sales-field">
              <span>{t("sales.orders.customer")}</span>
              <span className="latin muted">{order.customer_code} · {order.customer_name}</span>
            </label>
            <label className="sales-field">
              <span>{t("inventory.warehouse.label")}</span>
              <span className="latin muted">{order.warehouse_code}</span>
            </label>
          </div>

          <div className="sales-table-wrap">
            <table className="sales-table">
              <thead>
                <tr>
                  <th>{t("sales.newOrder.item")}</th>
                  <th className="sales-table__num">{t("inventory.onHand.quantity")}</th>
                  <th className="sales-table__num">{t("sales.newOrder.unitPrice")}</th>
                  <th className="sales-table__num">{t("sales.newOrder.discount")}</th>
                  <th className="sales-table__num">{t("sales.orders.total")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {lines.map((l, i) => {
                  const gross = Math.round((Number(l.quantity) || 0) * (parseToMinor(l.unit_price) ?? 0));
                  const lineTotal = gross - (parseToMinor(l.discount) ?? 0);
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
                      <td className="sales-table__num">
                        <input className="latin" inputMode="decimal" aria-label={t("inventory.onHand.quantity")} value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} />
                      </td>
                      <td className="sales-table__num">
                        <input className="latin" inputMode="decimal" aria-label={t("sales.newOrder.unitPrice")} value={l.unit_price} onChange={(e) => setLine(i, { unit_price: e.target.value })} placeholder="0.00" />
                      </td>
                      <td className="sales-table__num">
                        <input className="latin" inputMode="decimal" aria-label={t("sales.newOrder.discount")} value={l.discount} onChange={(e) => setLine(i, { discount: e.target.value })} placeholder="0.00" />
                      </td>
                      <td className="sales-table__num"><Bdi>{formatMinor(lineTotal)}</Bdi></td>
                      <td>
                        <button type="button" className="btn btn--sm btn--icon" onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))} disabled={lines.length <= 1} aria-label={t("common.delete")}><NavIcon name="close" /></button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={4}>{t("sales.newOrder.subtotal")}</td>
                  <td className="sales-table__num"><Bdi>{formatMinor(subtotal)}</Bdi></td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>

          <div className="sales-actions">
            <button type="button" className="btn btn--sm" onClick={() => setLines((ls) => [...ls, emptyLine()])}>
              {t("sales.newOrder.addLine")}
            </button>
            <button type="button" className="btn btn--sm btn--ghost" onClick={() => navigate(`/sales/orders/${id}`)}>
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
