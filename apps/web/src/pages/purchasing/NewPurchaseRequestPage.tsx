import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../../app/icons";
import { useLocation, useNavigate } from "react-router-dom";

import { createRequest, listSuppliers, type NewPOLine } from "../../api/purchasing";
import { listItems, listWarehouses } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { useFormKeys } from "../../hooks/useFormKeys";
import { useToast } from "../../app/ToastContext";
import { formatMinor, minorToAmount, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

interface DraftLine {
  item_sku: string;
  quantity: string;
  unit_cost: string;
}

const emptyLine = (): DraftLine => ({ item_sku: "", quantity: "", unit_cost: "" });

// Prefill carried by the Duplicate action on an existing purchase request (see the detail page).
interface DuplicateInit {
  supplier_code: string;
  warehouse_code: string;
  lines: { item_sku: string; quantity: string; unit_cost: number }[];
}

export function NewPurchaseRequestPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const dup = (useLocation().state as { duplicate?: DuplicateInit } | null)?.duplicate;
  const { data: suppliers } = useAsync(listSuppliers, [], "purchasing:suppliers");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");
  const { data: items } = useAsync(listItems, [], "inventory:items");

  const [supplier, setSupplier] = useState(dup?.supplier_code ?? "");
  const [warehouse, setWarehouse] = useState(dup?.warehouse_code ?? "");
  const [lines, setLines] = useState<DraftLine[]>(
    dup?.lines?.length
      ? dup.lines.map((l) => ({ item_sku: l.item_sku, quantity: l.quantity, unit_cost: minorToAmount(l.unit_cost) }))
      : [emptyLine()],
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ⌘/Ctrl+Enter submits, Esc cancels back to the purchase-requests list.
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef, onCancel: () => navigate("/purchasing/requests") });

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
      // The request detail page fires the rich "created" receipt on arrival.
      navigate(`/purchasing/requests/${req.id}`, { state: { feedback: "created" } });
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

      <form ref={formRef} className="card pur-page" onSubmit={onSubmit}>
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
            <span>{t("inventory.warehouse.label")}</span>
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
                      <button type="button" className="btn btn--sm btn--icon" onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))} disabled={lines.length <= 1} aria-label={t("common.delete")}><NavIcon name="close" /></button>
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
