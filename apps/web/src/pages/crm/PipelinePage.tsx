import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import {
  createOpportunity,
  getOpportunity,
  listOpportunities,
  type NewOppLine,
  type Opportunity,
} from "../../api/crm";
import { listCustomers } from "../../api/sales";
import { listItems, listWarehouses } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { prefetch } from "../../lib/prefetch";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { CrmNav } from "./CrmNav";
import "./crm.css";

interface DraftLine {
  item_sku: string;
  quantity: string;
  unit_price: string;
}

const emptyLine = (): DraftLine => ({ item_sku: "", quantity: "", unit_price: "" });

export function PipelinePage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(() => listOpportunities(), [], "crm:opportunities");
  const { data: customers } = useAsync(listCustomers, [], "sales:customers");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");
  const { data: items } = useAsync(listItems, [], "inventory:items");

  const [name, setName] = useState("");
  const [customer, setCustomer] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([emptyLine()]);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

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
    setFormError(null);
    if (!name) {
      setFormError(t("crm.newOpp.needName"));
      return;
    }
    const payloadLines: NewOppLine[] = [];
    for (const l of lines) {
      const price = parseToMinor(l.unit_price);
      if (!l.item_sku || !l.quantity) continue;
      if (price === null) {
        setFormError(t("crm.newOpp.badPrice"));
        return;
      }
      payloadLines.push({ item_sku: l.item_sku, quantity: l.quantity, unit_price: price });
    }
    setBusy(true);
    try {
      await createOpportunity({
        name,
        customer_code: customer,
        warehouse_code: warehouse,
        lines: payloadLines,
      });
      setName("");
      setCustomer("");
      setWarehouse("");
      setLines([emptyLine()]);
      reload();
      toast.show(t("crm.toast.opportunityCreated"), "success");
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setBusy(false);
    }
  }

  const stockItems = (items ?? []).filter((i) => i.type === "stock");

  return (
    <section className="crm-page">
      <CrmNav />

      <form className="card crm-page" onSubmit={onSubmit}>
        <h2>{t("crm.tabs.newOpp")}</h2>
        <div className="crm-toolbar">
          <label className="crm-field">
            <span>{t("crm.opp.name")}</span>
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="crm-field">
            <span>{t("crm.opp.customer")}</span>
            <select value={customer} onChange={(e) => setCustomer(e.target.value)}>
              <option value="">—</option>
              {(customers ?? []).map((c) => (
                <option key={c.code} value={c.code}>{c.code} · {c.name}</option>
              ))}
            </select>
          </label>
          <label className="crm-field">
            <span>{t("inventory.warehouse.code")}</span>
            <select value={warehouse} onChange={(e) => setWarehouse(e.target.value)}>
              <option value="">—</option>
              {(warehouses ?? []).map((w) => (
                <option key={w.code} value={w.code}>{w.code} · {w.name}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="crm-table-wrap">
          <table className="crm-table">
            <thead>
              <tr>
                <th>{t("sales.newOrder.item")}</th>
                <th className="crm-table__num">{t("inventory.onHand.quantity")}</th>
                <th className="crm-table__num">{t("sales.newOrder.unitPrice")}</th>
                <th className="crm-table__num">{t("sales.orders.total")}</th>
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
                    <td className="crm-table__num">
                      <input className="latin" inputMode="decimal" value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} />
                    </td>
                    <td className="crm-table__num">
                      <input className="latin" inputMode="decimal" value={l.unit_price} onChange={(e) => setLine(i, { unit_price: e.target.value })} placeholder="0.00" />
                    </td>
                    <td className="crm-table__num"><Bdi>{formatMinor(lineTotal)}</Bdi></td>
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
                <td className="crm-table__num"><Bdi>{formatMinor(subtotal)}</Bdi></td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>

        <div className="crm-actions">
          <button type="button" className="btn btn--sm" onClick={() => setLines((ls) => [...ls, emptyLine()])}>
            {t("sales.newOrder.addLine")}
          </button>
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {t("crm.newOpp.create")}
          </button>
        </div>
        {formError && <p className="error-text">{formError}</p>}
      </form>

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}
      {data && data.length === 0 && (
        <EmptyState title={t("crm.pipeline.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="card crm-table-wrap">
          <table className="crm-table">
            <thead>
              <tr>
                <th>{t("crm.opp.number")}</th>
                <th>{t("crm.opp.name")}</th>
                <th>{t("crm.opp.stage")}</th>
                <th className="crm-table__num">{t("crm.opp.amount")}</th>
                <th className="crm-table__num">{t("crm.opp.weighted")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((o: Opportunity) => (
                <tr key={o.id}>
                  <td>
                    <Link
                      to={`/crm/opportunities/${o.id}`}
                      className="latin"
                      onMouseEnter={() => prefetch(`crm:opportunity:${o.id}`, () => getOpportunity(o.id))}
                      onFocus={() => prefetch(`crm:opportunity:${o.id}`, () => getOpportunity(o.id))}
                    >
                      {o.number}
                    </Link>
                  </td>
                  <td>{o.name}</td>
                  <td>
                    <span className={`crm-badge crm-badge--${o.stage}`}>{t(`crm.stage.${o.stage}`)}</span>
                  </td>
                  <td className="crm-table__num"><Bdi>{formatMinor(o.amount_minor, o.currency)}</Bdi></td>
                  <td className="crm-table__num muted"><Bdi>{formatMinor(o.weighted_minor, o.currency)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
