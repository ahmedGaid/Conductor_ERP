import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../../app/icons";
import { useLocation, useNavigate } from "react-router-dom";

import { createPurchaseOrder, listSuppliers, type NewPOLine } from "../../api/purchasing";
import { listItems, listWarehouses } from "../../api/inventory";
import { listTaxCodes } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { useDraftRecovery } from "../../hooks/useDraftRecovery";
import { useFormKeys } from "../../hooks/useFormKeys";
import { useToast } from "../../app/ToastContext";
import { formatMinor, minorToAmount, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ComboBox } from "../../components/ComboBox";
import { DraftRecoveryBanner } from "../../components/DraftRecoveryBanner";
import { DraftStatusIndicator } from "../../components/DraftStatusIndicator";
import { useSetHelpSignals } from "../../help/HelpSignalsContext";
import { PurchasingNav } from "./PurchasingNav";
import { WorkflowTracker } from "../../components/WorkflowTracker";
import { workflowFor } from "../../lib/workflow";
import "./purchasing.css";

interface DraftLine {
  item_sku: string;
  quantity: string;
  unit_cost: string;
}

const emptyLine = (): DraftLine => ({ item_sku: "", quantity: "", unit_cost: "" });

// The shape autosaved as a draft. Kept as one object so the draft is a single value the hook can
// diff, while the fields stay in their own useState (the form reads/writes them field by field).
interface PurchaseOrderDraft {
  supplier: string;
  warehouse: string;
  taxCode: string;
  lines: DraftLine[];
}

const EMPTY_PO_DRAFT: PurchaseOrderDraft = { supplier: "", warehouse: "", taxCode: "", lines: [emptyLine()] };

// Prefill carried by the Duplicate action on an existing purchase order (see PurchaseOrderDetailPage).
interface DuplicateInit {
  supplier_code: string;
  warehouse_code: string;
  tax_code: string;
  lines: { item_sku: string; quantity: string; unit_cost: number }[];
}

export function NewPurchaseOrderPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const dup = (useLocation().state as { duplicate?: DuplicateInit } | null)?.duplicate;
  const { data: suppliers } = useAsync(listSuppliers, [], "purchasing:suppliers");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");
  const { data: items } = useAsync(listItems, [], "inventory:items");
  const { data: taxCodes } = useAsync(listTaxCodes, [], "accounting:tax-codes");

  const [supplier, setSupplier] = useState(dup?.supplier_code ?? "");
  const [warehouse, setWarehouse] = useState(dup?.warehouse_code ?? "");
  const [taxCode, setTaxCode] = useState(dup?.tax_code ?? "");
  const [lines, setLines] = useState<DraftLine[]>(
    dup?.lines?.length
      ? dup.lines.map((l) => ({ item_sku: l.item_sku, quantity: l.quantity, unit_cost: minorToAmount(l.unit_cost) }))
      : [emptyLine()],
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ⌘/Ctrl+Enter submits, Esc cancels back to the purchase-orders list.
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef, onCancel: () => navigate("/purchasing") });

  // Autosave the half-built purchase order so closing the tab (or a crash) doesn't lose it.
  const draft = useMemo<PurchaseOrderDraft>(
    () => ({ supplier, warehouse, taxCode, lines }),
    [supplier, warehouse, taxCode, lines],
  );
  const recovery = useDraftRecovery<PurchaseOrderDraft>({
    workflowKey: "purchasing.order.create",
    entityType: "purchase_order",
    value: draft,
    baseline: EMPTY_PO_DRAFT,
    schemaVersion: 1,
  });

  function applyDraft(d: PurchaseOrderDraft) {
    setSupplier(d.supplier ?? "");
    setWarehouse(d.warehouse ?? "");
    setTaxCode(d.taxCode ?? "");
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
  const taxRateBps = (taxCodes ?? []).find((c) => c.code === taxCode)?.rate_bps ?? 0;
  const vat = Math.round((subtotal * taxRateBps) / 10000);

  // Publish the page's live facts for the Help drawer's Live tab.
  useSetHelpSignals({
    supplierPicked: supplier !== "",
    warehousePicked: warehouse !== "",
    lineReady: lines.some((l) => l.item_sku && l.quantity && parseToMinor(l.unit_cost) !== null),
    hasError: error !== null,
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!supplier || !warehouse) {
      setError(t("purchasing.newOrder.pickSupplierWarehouse"));
      return;
    }
    const payloadLines: NewPOLine[] = [];
    for (const l of lines) {
      const cost = parseToMinor(l.unit_cost);
      if (!l.item_sku || !l.quantity) continue;
      if (cost === null) {
        setError(t("purchasing.newOrder.badCost"));
        return;
      }
      payloadLines.push({ item_sku: l.item_sku, quantity: l.quantity, unit_cost: cost });
    }
    if (payloadLines.length === 0) {
      setError(t("purchasing.newOrder.needLine"));
      return;
    }
    setBusy(true);
    try {
      const order = await createPurchaseOrder({ supplier_code: supplier, warehouse_code: warehouse, tax_code: taxCode, lines: payloadLines });
      // The workflow finished — the draft must not come back on the next visit.
      void recovery.complete(String(order.id));
      // The rich "created" receipt is fired on arrival by the order detail page (which owns the
      // optimistic runners its recommended-next step needs). We just hand it the event.
      navigate(`/purchasing/orders/${order.id}`, { state: { feedback: "created" } });
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setBusy(false);
    }
  }

  const stockItems = (items ?? []).filter((i) => i.type === "stock");

  return (
    <section className="pur-page">
      <PurchasingNav />

      {recovery.recoverable && (
        <DraftRecoveryBanner
          entityLabel={t("drafts.workflow.purchasing.order.create")}
          lastActiveAt={recovery.recoverable.lastActiveAt}
          onContinue={() => {
            const payload = recovery.recover();
            if (payload) applyDraft(payload);
          }}
          onDiscard={() => void recovery.discard()}
        />
      )}

      <form ref={formRef} className="card pur-page" onSubmit={onSubmit}>
        <WorkflowTracker kind="purchasing" steps={workflowFor("purchasing", "new")} />
        <div className="pur-toolbar">
          <label className="pur-field">
            <span>{t("purchasing.orders.supplier")}</span>
            <ComboBox
              value={supplier}
              onChange={setSupplier}
              placeholder={t("common.selectField", { field: t("purchasing.orders.supplier") })}
              options={(suppliers ?? []).map((s) => ({ value: s.code, label: `${s.code} · ${s.name}` }))}
            />
          </label>
          <label className="pur-field">
            <span>{t("inventory.warehouse.label")}</span>
            <ComboBox
              value={warehouse}
              onChange={setWarehouse}
              placeholder={t("common.selectField", { field: t("inventory.warehouse.label") })}
              options={(warehouses ?? []).map((w) => ({ value: w.code, label: `${w.code} · ${w.name}` }))}
            />
          </label>
          <label className="pur-field">
            <span>{t("purchasing.newOrder.taxCode")}</span>
            <ComboBox
              value={taxCode}
              onChange={setTaxCode}
              placeholder={t("purchasing.newOrder.noTax")}
              options={[{ value: "", label: t("purchasing.newOrder.noTax") }, ...(taxCodes ?? []).map((c) => ({ value: c.code, label: `${c.code} · ${c.name}` }))]}
            />
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
              {vat > 0 && (
                <tr>
                  <td colSpan={3}>{t("purchasing.detail.vat")}</td>
                  <td className="pur-table__num"><Bdi>{formatMinor(vat)}</Bdi></td>
                  <td />
                </tr>
              )}
              <tr>
                <td colSpan={3}>{t("accounting.entry.totals")}</td>
                <td className="pur-table__num"><Bdi>{formatMinor(subtotal + vat)}</Bdi></td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>

        <div className="pur-actions">
          <button type="button" className="btn btn--sm" onClick={() => setLines((ls) => [...ls, emptyLine()])}>
            {t("purchasing.newOrder.addLine")}
          </button>
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {t("purchasing.newOrder.create")}
          </button>
          {recovery.conflict && <p className="muted" role="status">{t("drafts.conflict")}</p>}
          <DraftStatusIndicator status={recovery.status} savedAt={recovery.savedAt} />
        </div>
        {error && <p className="error-text">{error}</p>}
      </form>
    </section>
  );
}
