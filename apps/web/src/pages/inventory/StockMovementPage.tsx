import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import {
  issueStock,
  listItems,
  listMovements,
  listWarehouses,
  receiveStock,
  transferStock,
  type MovementType,
} from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { useActionFeedback } from "../../app/ActionFeedbackContext";
import { showMovementReceipt, showMovementError } from "../../lib/feedback/inventory";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { EntityLink } from "../../components/EntityLink";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

const MODES: MovementType[] = ["receipt", "issue", "transfer"];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function StockMovementPage() {
  const { t } = useTranslation();
  const fb = useActionFeedback();
  const { data: items } = useAsync(listItems, [], "inventory:items");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");
  const { data: movements, reload } = useAsync(() => listMovements(), [], "inventory:movements");

  // A deep link can prefill the form (e.g. an "insufficient stock" error receipt links here to
  // receive the exact short item at the order's warehouse): ?mode=receipt&item=SKU&warehouse=WH.
  const [params] = useSearchParams();
  const paramMode = params.get("mode");
  const initialMode: MovementType = MODES.includes(paramMode as MovementType) ? (paramMode as MovementType) : "receipt";

  const [mode, setMode] = useState<MovementType>(initialMode);
  const [itemSku, setItemSku] = useState(params.get("item") ?? "");
  const [warehouse, setWarehouse] = useState(params.get("warehouse") ?? "");
  const [dest, setDest] = useState("");
  const [quantity, setQuantity] = useState(params.get("qty") ?? "");
  const [unitCost, setUnitCost] = useState("");
  const [batchNo, setBatchNo] = useState("");
  const [expiry, setExpiry] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!itemSku || !warehouse || !quantity) {
      setError(t("inventory.movement.fillRequired"));
      return;
    }
    if (mode === "transfer" && !dest) {
      setError(t("inventory.movement.fillRequired"));
      return;
    }
    let cost = 0;
    if (mode === "receipt") {
      const parsed = parseToMinor(unitCost);
      if (parsed === null) {
        setError(t("inventory.movement.badCost"));
        return;
      }
      cost = parsed;
    }
    setBusy(true);
    try {
      const mv =
        mode === "receipt"
          ? await receiveStock({
              item_sku: itemSku, warehouse_code: warehouse, quantity, unit_cost: cost, date: today(),
              batch_no: batchNo || undefined, expiry_date: expiry || null,
            })
          : mode === "issue"
            ? await issueStock({ item_sku: itemSku, warehouse_code: warehouse, quantity, date: today() })
            : await transferStock({ item_sku: itemSku, source_code: warehouse, dest_code: dest, quantity, date: today() });
      // The posted movement floats a receipt (what moved + journal + resulting on-hand), replacing
      // the old one-line toast.
      showMovementReceipt(fb, t, mv, mode);
      setQuantity("");
      setUnitCost("");
      setBatchNo("");
      setExpiry("");
      reload();
    } catch (err) {
      // A failed issue / transfer is almost always short stock — the error receipt offers a one-click
      // receive of the same item + warehouse to clear it.
      showMovementError(fb, t, { mode, itemSku, warehouse }, err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="inv-page">
      <InventoryNav />

      <form className="card inv-page" onSubmit={onSubmit}>
        <div className="inv-segment" role="group" aria-label={t("inventory.movement.type")}>
          {MODES.map((m) => (
            <button
              key={m}
              type="button"
              className={m === mode ? "inv-segment__btn inv-segment__btn--active" : "inv-segment__btn"}
              aria-pressed={m === mode}
              onClick={() => setMode(m)}
            >
              {t(`inventory.movement.${m}`)}
            </button>
          ))}
        </div>

        <div className="inv-toolbar">
          <label className="inv-field">
            <span>{t("inventory.item.sku")}</span>
            <select value={itemSku} onChange={(e) => setItemSku(e.target.value)}>
              <option value="">—</option>
              {(items ?? []).filter((i) => i.type === "stock").map((i) => (
                <option key={i.sku} value={i.sku}>{i.sku} · {i.name}</option>
              ))}
            </select>
          </label>

          <label className="inv-field">
            <span>{mode === "transfer" ? t("inventory.movement.from") : t("inventory.warehouse.code")}</span>
            <select value={warehouse} onChange={(e) => setWarehouse(e.target.value)}>
              <option value="">—</option>
              {(warehouses ?? []).map((w) => (
                <option key={w.code} value={w.code}>{w.code} · {w.name}</option>
              ))}
            </select>
          </label>

          {mode === "transfer" && (
            <label className="inv-field">
              <span>{t("inventory.movement.to")}</span>
              <select value={dest} onChange={(e) => setDest(e.target.value)}>
                <option value="">—</option>
                {(warehouses ?? []).map((w) => (
                  <option key={w.code} value={w.code}>{w.code} · {w.name}</option>
                ))}
              </select>
            </label>
          )}

          <label className="inv-field">
            <span>{t("inventory.onHand.quantity")}</span>
            <input className="latin" inputMode="decimal" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </label>

          {mode === "receipt" && (
            <label className="inv-field">
              <span>{t("inventory.movement.unitCost")}</span>
              <input className="latin" inputMode="decimal" value={unitCost} onChange={(e) => setUnitCost(e.target.value)} placeholder="0.00" />
            </label>
          )}

          {mode === "receipt" && (
            <label className="inv-field">
              <span>{t("inventory.movement.batchNo")}</span>
              <input className="latin" value={batchNo} onChange={(e) => setBatchNo(e.target.value)} placeholder={t("inventory.movement.optional")} />
            </label>
          )}

          {mode === "receipt" && (
            <label className="inv-field">
              <span>{t("inventory.movement.expiry")}</span>
              <input className="latin" type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} />
            </label>
          )}

          <button className="btn btn--primary" type="submit" disabled={busy}>
            {t("inventory.movement.post")}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
      </form>

      {movements && movements.length > 0 && (
        <div className="card inv-table-wrap">
          <table className="inv-table">
            <thead>
              <tr>
                <th>{t("inventory.movement.type")}</th>
                <th>{t("inventory.item.sku")}</th>
                <th>{t("inventory.warehouse.code")}</th>
                <th className="inv-table__num">{t("inventory.onHand.quantity")}</th>
                <th className="inv-table__num">{t("inventory.onHand.value")}</th>
                <th>{t("accounting.journals.number")}</th>
              </tr>
            </thead>
            <tbody>
              {movements.map((m) => (
                <tr key={m.id}>
                  <td>{t(`inventory.movement.${m.type}`)}</td>
                  <td><EntityLink type="item" value={m.item_sku} /></td>
                  <td>
                    <EntityLink type="warehouse" value={m.warehouse_code} />
                    {m.dest_warehouse_code && <> → <EntityLink type="warehouse" value={m.dest_warehouse_code} /></>}
                  </td>
                  <td className="inv-table__num"><Bdi>{m.quantity}</Bdi></td>
                  <td className="inv-table__num"><Bdi>{formatMinor(m.value_minor)}</Bdi></td>
                  <td className="latin">{m.journal_number ? <EntityLink type="journal" value={m.journal_number} /> : <span className="muted">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
