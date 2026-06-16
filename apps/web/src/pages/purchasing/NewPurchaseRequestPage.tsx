import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createRequest, listSuppliers, type NewPOLine } from "../../api/purchasing";
import { listItems, listWarehouses } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

interface DraftLine {
  item_sku: string;
  quantity: string;
  unit_cost: string;
}

const emptyLine = (): DraftLine => ({ item_sku: "", quantity: "", unit_cost: "" });

export function NewPurchaseRequestPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: suppliers } = useAsync(listSuppliers, [], "purchasing:suppliers");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");
  const { data: items } = useAsync(listItems, [], "inventory:items");

  const [supplier, setSupplier] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([emptyLine()]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      const req = await createRequest({ supplier_code: supplier, warehouse_code: warehouse, lines: payloadLines });
      navigate(`/purchasing/requests/${req.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const stockItems = (items ?? []).filter((i) => i.type === "stock");

  return (
    <section className="pur-page">
      <h1>{t("nav.purchasing")}</h1>
      <PurchasingNav />

      <form className="card pur-page" onSubmit={onSubmit}>
        <div className="pur-toolbar">
          <label className="pur-field">
            <span>{t("purchasing.orders.supplier")}</span>
            <select value={supplier} onChange={(e) => setSupplier(e.target.value)}>
              <option value="">—</option>
              {(suppliers ?? []).map((s) => (
                <option key={s.code} value={s.code}>{s.code} · {s.name}</option>
              ))}
            </select>
          </label>
          <label className="pur-field">
            <span>{t("inventory.warehouse.code")}</span>
            <select value={warehouse} onChange={(e) => setWarehouse(e.target.value)}>
              <option value="">—</option>
              {(warehouses ?? []).map((w) => (
                <option key={w.code} value={w.code}>{w.code} · {w.name}</option>
              ))}
            </select>
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
                      <select value={l.item_sku} onChange={(e) => setLine(i, { item_sku: e.target.value })}>
                        <option value="">—</option>
                        {stockItems.map((it) => (
                          <option key={it.sku} value={it.sku}>{it.sku} · {it.name}</option>
                        ))}
                      </select>
                    </td>
                    <td className="pur-table__num">
                      <input className="latin" inputMode="decimal" value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} />
                    </td>
                    <td className="pur-table__num">
                      <input className="latin" inputMode="decimal" value={l.unit_cost} onChange={(e) => setLine(i, { unit_cost: e.target.value })} placeholder="0.00" />
                    </td>
                    <td className="pur-table__num"><Bdi>{formatMinor(lineTotal)}</Bdi></td>
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
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {t("purchasing.requests.create")}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </form>
    </section>
  );
}
