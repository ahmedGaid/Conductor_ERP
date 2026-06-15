import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createOrder, listCustomers, type NewOrderLine } from "../../api/sales";
import { listItems, listWarehouses } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { SalesNav } from "./SalesNav";
import "./sales.css";

interface DraftLine {
  item_sku: string;
  quantity: string;
  unit_price: string;
}

const emptyLine = (): DraftLine => ({ item_sku: "", quantity: "", unit_price: "" });

export function NewOrderPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: customers } = useAsync(listCustomers, []);
  const { data: warehouses } = useAsync(listWarehouses, []);
  const { data: items } = useAsync(listItems, []);

  const [customer, setCustomer] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([emptyLine()]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function setLine(i: number, patch: Partial<DraftLine>) {
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  const subtotal = lines.reduce((s, l) => {
    const qty = Number(l.quantity) || 0;
    const price = parseToMinor(l.unit_price) ?? 0;
    return s + Math.round(qty * price);
  }, 0);

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
      payloadLines.push({ item_sku: l.item_sku, quantity: l.quantity, unit_price: price });
    }
    if (payloadLines.length === 0) {
      setError(t("sales.newOrder.needLine"));
      return;
    }
    setBusy(true);
    try {
      const order = await createOrder({ customer_code: customer, warehouse_code: warehouse, lines: payloadLines });
      navigate(`/sales/orders/${order.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const stockItems = (items ?? []).filter((i) => i.type === "stock");

  return (
    <section className="sales-page">
      <h1>{t("nav.sales")}</h1>
      <SalesNav />

      <form className="card sales-page" onSubmit={onSubmit}>
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
        </div>

        <div className="sales-table-wrap">
          <table className="sales-table">
            <thead>
              <tr>
                <th>{t("sales.newOrder.item")}</th>
                <th className="sales-table__num">{t("inventory.onHand.quantity")}</th>
                <th className="sales-table__num">{t("sales.newOrder.unitPrice")}</th>
                <th className="sales-table__num">{t("sales.orders.total")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {lines.map((l, i) => {
                const lineTotal = Math.round((Number(l.quantity) || 0) * (parseToMinor(l.unit_price) ?? 0));
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
                <td colSpan={3}>{t("accounting.entry.totals")}</td>
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
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {t("sales.newOrder.create")}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </form>
    </section>
  );
}
