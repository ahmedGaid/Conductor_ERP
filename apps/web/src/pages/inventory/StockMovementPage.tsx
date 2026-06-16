import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

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
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

const MODES: MovementType[] = ["receipt", "issue", "transfer"];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function StockMovementPage() {
  const { t } = useTranslation();
  const { data: items } = useAsync(listItems, [], "inventory:items");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");
  const { data: movements, reload } = useAsync(() => listMovements(), [], "inventory:movements");

  const [mode, setMode] = useState<MovementType>("receipt");
  const [itemSku, setItemSku] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [dest, setDest] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitCost, setUnitCost] = useState("");
  const [batchNo, setBatchNo] = useState("");
  const [expiry, setExpiry] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    if (!itemSku || !warehouse || !quantity) {
      setError(t("inventory.movement.fillRequired"));
      return;
    }
    setBusy(true);
    try {
      if (mode === "receipt") {
        const cost = parseToMinor(unitCost);
        if (cost === null) {
          setError(t("inventory.movement.badCost"));
          return;
        }
        const mv = await receiveStock({
          item_sku: itemSku, warehouse_code: warehouse, quantity, unit_cost: cost, date: today(),
          batch_no: batchNo || undefined, expiry_date: expiry || null,
        });
        setOk(t("inventory.movement.posted", { ref: mv.journal_number || mv.id.slice(0, 8) }));
      } else if (mode === "issue") {
        const mv = await issueStock({ item_sku: itemSku, warehouse_code: warehouse, quantity, date: today() });
        setOk(t("inventory.movement.posted", { ref: mv.journal_number || mv.id.slice(0, 8) }));
      } else {
        if (!dest) {
          setError(t("inventory.movement.fillRequired"));
          return;
        }
        const mv = await transferStock({
          item_sku: itemSku, source_code: warehouse, dest_code: dest, quantity, date: today(),
        });
        setOk(t("inventory.movement.posted", { ref: mv.id.slice(0, 8) }));
      }
      setQuantity("");
      setUnitCost("");
      setBatchNo("");
      setExpiry("");
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="inv-page">
      <h1>{t("nav.inventory")}</h1>
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
        {ok && <p className="inv-ok">{ok}</p>}
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
                  <td><Bdi>{m.item_sku}</Bdi></td>
                  <td>
                    <Bdi>{m.warehouse_code}</Bdi>
                    {m.dest_warehouse_code && <> → <Bdi>{m.dest_warehouse_code}</Bdi></>}
                  </td>
                  <td className="inv-table__num"><Bdi>{m.quantity}</Bdi></td>
                  <td className="inv-table__num"><Bdi>{formatMinor(m.value_minor)}</Bdi></td>
                  <td className="latin muted">{m.journal_number || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
