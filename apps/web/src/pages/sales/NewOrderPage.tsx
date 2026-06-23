import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createOrder, listCustomers, type NewOrderLine } from "../../api/sales";
import { listItems, listWarehouses } from "../../api/inventory";
import { listTaxCodes } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { useFormKeys } from "../../hooks/useFormKeys";
import { useToast } from "../../app/ToastContext";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { SalesNav } from "./SalesNav";
import "./sales.css";

interface DraftLine {
  item_sku: string;
  quantity: string;
  unit_price: string;
  discount: string;
}

const emptyLine = (): DraftLine => ({ item_sku: "", quantity: "", unit_price: "", discount: "" });

export function NewOrderPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { data: customers } = useAsync(listCustomers, [], "sales:customers");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");
  const { data: items } = useAsync(listItems, [], "inventory:items");
  const { data: taxCodes } = useAsync(listTaxCodes, [], "accounting:tax-codes");

  const [customer, setCustomer] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [taxCode, setTaxCode] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([emptyLine()]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ⌘/Ctrl+Enter submits, Esc cancels back to the orders list.
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef, onCancel: () => navigate("/sales") });

  function setLine(i: number, patch: Partial<DraftLine>) {
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  const subtotal = lines.reduce((s, l) => {
    const qty = Number(l.quantity) || 0;
    const price = parseToMinor(l.unit_price) ?? 0;
    const discount = parseToMinor(l.discount) ?? 0;
    return s + Math.round(qty * price) - discount;
  }, 0);
  const taxRateBps = (taxCodes ?? []).find((c) => c.code === taxCode)?.rate_bps ?? 0;
  const vat = Math.round((subtotal * taxRateBps) / 10000);

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
      toast.show(t("sales.toast.orderCreated"), "success");
      navigate(`/sales/orders/${order.id}`);
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

      <form ref={formRef} className="card sales-page" onSubmit={onSubmit}>
        <div className="sales-toolbar">
          <label className="sales-field">
            <span>{t("sales.orders.customer")}</span>
            <select value={customer} onChange={(e) => setCustomer(e.target.value)}>
              <option value="">—</option>
              {(customers ?? []).map((c) => (
                <option key={c.code} value={c.code}>{c.code} · {c.name}</option>
              ))}
            </select>
          </label>
          <label className="sales-field">
            <span>{t("inventory.warehouse.code")}</span>
            <select value={warehouse} onChange={(e) => setWarehouse(e.target.value)}>
              <option value="">—</option>
              {(warehouses ?? []).map((w) => (
                <option key={w.code} value={w.code}>{w.code} · {w.name}</option>
              ))}
            </select>
          </label>
          <label className="sales-field">
            <span>{t("sales.newOrder.taxCode")}</span>
            <select value={taxCode} onChange={(e) => setTaxCode(e.target.value)}>
              <option value="">{t("sales.newOrder.noTax")}</option>
              {(taxCodes ?? []).map((c) => (
                <option key={c.code} value={c.code}>{c.code} · {c.name}</option>
              ))}
            </select>
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
                      <select value={l.item_sku} onChange={(e) => setLine(i, { item_sku: e.target.value })}>
                        <option value="">—</option>
                        {stockItems.map((it) => (
                          <option key={it.sku} value={it.sku}>{it.sku} · {it.name}</option>
                        ))}
                      </select>
                    </td>
                    <td className="sales-table__num">
                      <input className="latin" inputMode="decimal" value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} />
                    </td>
                    <td className="sales-table__num">
                      <input className="latin" inputMode="decimal" value={l.unit_price} onChange={(e) => setLine(i, { unit_price: e.target.value })} placeholder="0.00" />
                    </td>
                    <td className="sales-table__num">
                      <input className="latin" inputMode="decimal" value={l.discount} onChange={(e) => setLine(i, { discount: e.target.value })} placeholder="0.00" />
                    </td>
                    <td className="sales-table__num"><Bdi>{formatMinor(lineTotal)}</Bdi></td>
                    <td>
                      <button type="button" className="btn btn--sm" onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))} disabled={lines.length <= 1} aria-label={t("common.delete")}>✕</button>
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
        </div>
        {error && <p className="error-text">{error}</p>}
      </form>
    </section>
  );
}
