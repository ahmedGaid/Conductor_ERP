import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../../app/icons";
import { useLocation, useNavigate } from "react-router-dom";

import { markFormDirty } from "../../assistant/context";
import { createOrder, listCustomers, type NewOrderLine } from "../../api/sales";
import { listItems, listWarehouses } from "../../api/inventory";
import { listTaxCodes } from "../../api/accounting";
import { resolvePrice, type PriceResolution } from "../../api/pricing";
import { useAsync } from "../../hooks/useAsync";
import { useDraftRecovery } from "../../hooks/useDraftRecovery";
import { useFormKeys } from "../../hooks/useFormKeys";
import { useSmartDefault } from "../../hooks/useSmartDefault";
import { useToast } from "../../app/ToastContext";
import { setLastUsed } from "../../lib/lastUsed";
import { formatMinor, minorToAmount, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ComboBox } from "../../components/ComboBox";
import { DraftRecoveryBanner } from "../../components/DraftRecoveryBanner";
import { DraftStatusIndicator } from "../../components/DraftStatusIndicator";
import { useSetHelpSignals } from "../../help/HelpSignalsContext";
import { SalesNav } from "./SalesNav";
import { WorkflowTracker } from "../../components/WorkflowTracker";
import { workflowFor } from "../../lib/workflow";
import "./sales.css";

interface DraftLine {
  item_sku: string;
  quantity: string;
  unit_price: string;
  discount: string;
  priceSource?: string;
}

const emptyLine = (): DraftLine => ({ item_sku: "", quantity: "1", unit_price: "", discount: "" });

// The shape autosaved as a draft. Kept as one object so the draft is a single value the hook can
// diff, while the fields stay in their own useState (the form reads/writes them field by field).
interface OrderDraft {
  customer: string;
  warehouse: string;
  taxCode: string;
  lines: DraftLine[];
}

const EMPTY_ORDER_DRAFT: OrderDraft = { customer: "", warehouse: "", taxCode: "", lines: [emptyLine()] };

// Prefill carried by the Duplicate action on an existing order (see OrderDetailPage). Prices/discounts
// arrive as integer minor units and are shown as editable major-unit strings.
interface DuplicateInit {
  customer_code: string;
  warehouse_code: string;
  tax_code: string;
  lines: { item_sku: string; quantity: string; unit_price: number; discount: number }[];
}

export function NewOrderPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const dup = (useLocation().state as { duplicate?: DuplicateInit } | null)?.duplicate;
  const { data: customers } = useAsync(listCustomers, [], "sales:customers");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");
  const { data: items } = useAsync(listItems, [], "inventory:items");
  const { data: taxCodes } = useAsync(listTaxCodes, [], "accounting:tax-codes");

  const [customer, setCustomer] = useState(dup?.customer_code ?? "");
  const [warehouse, setWarehouse] = useState(dup?.warehouse_code ?? "");
  const [taxCode, setTaxCode] = useState(dup?.tax_code ?? "");
  const [lines, setLines] = useState<DraftLine[]>(
    dup?.lines?.length
      ? dup.lines.map((l) => ({
          item_sku: l.item_sku,
          quantity: l.quantity,
          unit_price: minorToAmount(l.unit_price),
          discount: l.discount ? minorToAmount(l.discount) : "",
        }))
      : [emptyLine()],
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Smart defaults: pre-fill the customer/warehouse/tax the user picked last time (or the only
  // option when there's just one), so a new order doesn't make you re-pick the obvious.
  useSmartDefault(customers, "sales:customer", customer, setCustomer, { single: false });
  useSmartDefault(warehouses, "warehouse", warehouse, setWarehouse);
  useSmartDefault(taxCodes, "sales:tax", taxCode, setTaxCode);

  // ⌘/Ctrl+Enter submits, Esc cancels back to the orders list.
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef, onCancel: () => navigate("/sales") });

  // The AI assistant's page envelope warns about unsaved changes before suggesting navigation.
  useEffect(() => {
    const isDirty = Boolean(customer || warehouse || taxCode)
      || lines.some((l) => l.item_sku || l.unit_price || l.discount);
    markFormDirty(isDirty);
    return () => markFormDirty(false);
  }, [customer, warehouse, taxCode, lines]);

  // Autosave the half-built order so closing the tab (or a crash) doesn't lose it.
  const draft = useMemo<OrderDraft>(
    () => ({ customer, warehouse, taxCode, lines }),
    [customer, warehouse, taxCode, lines],
  );
  const recovery = useDraftRecovery<OrderDraft>({
    workflowKey: "sales.order.create",
    entityType: "order",
    value: draft,
    baseline: EMPTY_ORDER_DRAFT,
    schemaVersion: 1,
  });

  function applyDraft(d: OrderDraft) {
    setCustomer(d.customer ?? "");
    setWarehouse(d.warehouse ?? "");
    setTaxCode(d.taxCode ?? "");
    setLines(d.lines?.length ? d.lines : [emptyLine()]);
  }

  function setLine(i: number, patch: Partial<DraftLine>) {
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  function sourceLabel(res: PriceResolution): string {
    return res.source === "customer_item"
      ? t("pricing.source.negotiated")
      : t("pricing.source.fromList", { list: res.price_list_code ?? "" });
  }

  // Pick an item, then ask pricing for its price for this customer (best-effort): fill the line's
  // unit price (net — tax-inclusive lists are backed out by the order's tax code) and note the source.
  async function onPickItem(i: number, sku: string) {
    setLine(i, { item_sku: sku, priceSource: undefined });
    if (!sku || !customer) return;
    try {
      const res = await resolvePrice({
        customer, sku, qty: lines[i]?.quantity || undefined, taxCode: taxCode || undefined,
      });
      if (res) setLine(i, { unit_price: minorToAmount(res.unit_price_minor), priceSource: sourceLabel(res) });
    } catch {
      /* prefill is a convenience — never block entry on a pricing lookup failure */
    }
  }

  const subtotal = lines.reduce((s, l) => {
    const qty = Number(l.quantity) || 0;
    const price = parseToMinor(l.unit_price) ?? 0;
    const discount = parseToMinor(l.discount) ?? 0;
    return s + Math.round(qty * price) - discount;
  }, 0);
  const taxRateBps = (taxCodes ?? []).find((c) => c.code === taxCode)?.rate_bps ?? 0;
  const vat = Math.round((subtotal * taxRateBps) / 10000);

  // Publish the page's live facts for the Help drawer's Live tab.
  useSetHelpSignals({
    customerPicked: customer !== "",
    warehousePicked: warehouse !== "",
    lineReady: lines.some((l) => l.item_sku && l.quantity && parseToMinor(l.unit_price) !== null),
    hasError: error !== null,
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!customer || !warehouse) {
      setError(t("sales.newOrder.pickCustomerWarehouse"));
      return;
    }
    const payloadLines: NewOrderLine[] = [];
    for (const l of lines) {
      const price = parseToMinor(l.unit_price);
      if (!l.item_sku || !l.quantity) continue;
      if (price === null) {
        setError(t("sales.newOrder.badPrice"));
        return;
      }
      const discount = l.discount ? parseToMinor(l.discount) : 0;
      if (discount === null) {
        setError(t("sales.newOrder.badPrice"));
        return;
      }
      payloadLines.push({ item_sku: l.item_sku, quantity: l.quantity, unit_price: price, discount });
    }
    if (payloadLines.length === 0) {
      setError(t("sales.newOrder.needLine"));
      return;
    }
    setBusy(true);
    try {
      const order = await createOrder({ customer_code: customer, warehouse_code: warehouse, tax_code: taxCode, lines: payloadLines });
      setLastUsed("sales:customer", customer);
      setLastUsed("warehouse", warehouse);
      setLastUsed("sales:tax", taxCode);
      // The workflow finished — the draft must not come back on the next visit.
      void recovery.complete(String(order.id));
      // The rich "created" receipt is fired on arrival by the order detail page (which owns the
      // optimistic runners its recommended-next step needs). We just hand it the event.
      navigate(`/sales/orders/${order.id}`, { state: { feedback: "created" } });
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setBusy(false);
    }
  }

  const stockItems = (items ?? []).filter((i) => i.type === "stock");

  return (
    <section className="sales-page">
      <SalesNav />

      {recovery.recoverable && (
        <DraftRecoveryBanner
          entityLabel={t("drafts.workflow.sales.order.create")}
          lastActiveAt={recovery.recoverable.lastActiveAt}
          onContinue={() => {
            const payload = recovery.recover();
            if (payload) applyDraft(payload);
          }}
          onDiscard={() => void recovery.discard()}
        />
      )}

      <form ref={formRef} className="card sales-page" onSubmit={onSubmit}>
        <WorkflowTracker kind="sales" steps={workflowFor("sales", "new")} />
        <div className="sales-toolbar">
          <label className="sales-field">
            <span>{t("sales.orders.customer")}</span>
            <ComboBox
              value={customer}
              onChange={setCustomer}
              placeholder={t("common.selectField", { field: t("sales.orders.customer") })}
              options={(customers ?? []).map((c) => ({ value: c.code, label: `${c.code} · ${c.name}` }))}
            />
          </label>
          <label className="sales-field">
            <span>{t("inventory.warehouse.label")}</span>
            <ComboBox
              value={warehouse}
              onChange={setWarehouse}
              placeholder={t("common.selectField", { field: t("inventory.warehouse.label") })}
              options={(warehouses ?? []).map((w) => ({ value: w.code, label: `${w.code} · ${w.name}` }))}
            />
          </label>
          <label className="sales-field">
            <span>{t("sales.newOrder.taxCode")}</span>
            <ComboBox
              value={taxCode}
              onChange={setTaxCode}
              placeholder={t("sales.newOrder.noTax")}
              options={[{ value: "", label: t("sales.newOrder.noTax") }, ...(taxCodes ?? []).map((c) => ({ value: c.code, label: `${c.code} · ${c.name}` }))]}
            />
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
                        onChange={(v) => void onPickItem(i, v)}
                        placeholder={t("common.selectField", { field: t("sales.newOrder.item") })}
                        options={stockItems.map((it) => ({ value: it.sku, label: `${it.sku} · ${it.name}` }))}
                      />
                    </td>
                    <td className="sales-table__num">
                      <input className="latin" inputMode="decimal" aria-label={t("inventory.onHand.quantity")} value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} />
                    </td>
                    <td className="sales-table__num">
                      <input className="latin" inputMode="decimal" aria-label={t("sales.newOrder.unitPrice")} value={l.unit_price} onChange={(e) => setLine(i, { unit_price: e.target.value, priceSource: undefined })} placeholder="0.00" />
                      {l.priceSource && <span className="sales-price-source">{l.priceSource}</span>}
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
              {vat > 0 && (
                <tr>
                  <td colSpan={4}>{t("sales.detail.vat")}</td>
                  <td className="sales-table__num"><Bdi>{formatMinor(vat)}</Bdi></td>
                  <td />
                </tr>
              )}
              <tr>
                <td colSpan={4}>{t("accounting.entry.totals")}</td>
                <td className="sales-table__num"><Bdi>{formatMinor(subtotal + vat)}</Bdi></td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>

        <div className="sales-actions">
          <button type="button" className="btn btn--sm" onClick={() => setLines((ls) => [...ls, emptyLine()])}>
            {t("sales.newOrder.addLine")}
          </button>
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {t("sales.newOrder.create")}
          </button>
          {recovery.conflict && <p className="muted" role="status">{t("drafts.conflict")}</p>}
          <DraftStatusIndicator status={recovery.status} savedAt={recovery.savedAt} />
        </div>
        {error && <p className="error-text">{error}</p>}
      </form>
    </section>
  );
}
