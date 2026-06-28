import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  addCustomerPrice,
  deleteAssignment,
  deleteCustomerPrice,
  listAssignments,
  listCustomerPrices,
  listPriceLists,
  setAssignment,
  type CustomerAssignment,
  type CustomerItemPrice,
} from "../../api/pricing";
import { listCustomers } from "../../api/sales";
import { listItems } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { EmptyState } from "../../components/EmptyState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate, runOptimistic } from "../../lib/optimistic";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { PricingTabs } from "./PricingTabs";
import "./pricing.css";

export function CustomerPricingPage() {
  const { t } = useTranslation();
  const toast = useToast();

  const { data: customers } = useAsync(listCustomers, [], "sales:customers");
  const { data: items } = useAsync(listItems, [], "inventory:items");
  const { data: lists } = useAsync(listPriceLists, [], "pricing:lists");
  const stockItems = (items ?? []).filter((i) => i.type === "stock");
  const activeLists = (lists ?? []).filter((l) => l.is_active);

  return (
    <section className="pricing-page">
      <div className="pricing-head">
        <h1>{t("pricing.title")}</h1>
        <p className="muted">{t("pricing.customers.subtitle")}</p>
      </div>

      <PricingTabs active="customers" />

      <AssignmentsBlock customers={customers ?? []} lists={activeLists} t={t} toast={toast} />
      <OverridesBlock customers={customers ?? []} items={stockItems} t={t} toast={toast} />
    </section>
  );
}

type Customer = { code: string; name: string };
type StockItem = { sku: string; name: string };
type PriceListLite = { code: string; name: string };
type TFn = ReturnType<typeof useTranslation>["t"];
type Toast = ReturnType<typeof useToast>;

// ── Customer → price-list assignments ─────────────────────────────────────────────────────────────
function AssignmentsBlock({
  customers,
  lists,
  t,
  toast,
}: {
  customers: Customer[];
  lists: PriceListLite[];
  t: TFn;
  toast: Toast;
}) {
  const { data, loading, error, reload, mutate } = useAsync(listAssignments, [], "pricing:assignments");
  const [customer, setCustomer] = useState("");
  const [listCode, setListCode] = useState("");

  function onAssign(e: FormEvent) {
    e.preventDefault();
    const c = customer.trim();
    const l = listCode.trim();
    if (!c || !l) return;
    // Upsert: one assignment per customer, so replace any existing row for this customer.
    const tempId = `tmp-${Date.now()}`;
    const placeholder: CustomerAssignment = { id: tempId, customer_code: c, price_list_code: l };
    void runOptimistic<CustomerAssignment[], CustomerAssignment>({
      current: data ?? [],
      mutate,
      optimistic: (cur) => [placeholder, ...cur.filter((r) => r.customer_code !== c)],
      request: () => setAssignment({ customer_code: c, price_list_code: l }),
      settle: (predicted, saved) => predicted.map((r) => (r.id === tempId ? saved : r)),
      toast,
      success: t("pricing.toast.assigned"),
    });
    setCustomer("");
    setListCode("");
  }

  function onRemove(row: CustomerAssignment) {
    void runOptimistic<CustomerAssignment[], void>({
      current: data ?? [],
      mutate,
      optimistic: (cur) => cur.filter((r) => r.id !== row.id),
      request: () => deleteAssignment(row.id),
      toast,
      success: t("pricing.toast.assignmentRemoved"),
    });
  }

  const nameOf = (code: string) => customers.find((c) => c.code === code)?.name;

  return (
    <div className="pricing-block">
      <h2 className="pricing-block__title">{t("pricing.customers.assignTitle")}</h2>
      <p className="muted pricing-block__hint">{t("pricing.customers.assignHint")}</p>

      <form className="card pricing-toolbar" onSubmit={onAssign}>
        <label className="pricing-field">
          <span>{t("pricing.customers.customer")}</span>
          <select value={customer} onChange={(e) => setCustomer(e.target.value)}>
            <option value="">—</option>
            {customers.map((c) => (
              <option key={c.code} value={c.code}>
                {c.code} · {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="pricing-field">
          <span>{t("pricing.customers.priceList")}</span>
          <select value={listCode} onChange={(e) => setListCode(e.target.value)}>
            <option value="">—</option>
            {lists.map((l) => (
              <option key={l.code} value={l.code}>
                {l.code} · {l.name}
              </option>
            ))}
          </select>
        </label>
        <button className="btn btn--primary" type="submit">
          {t("pricing.customers.assign")}
        </button>
      </form>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("pricing.customers.assignEmpty")} hint={t("pricing.customers.assignEmptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="card pricing-table-wrap">
          <table className="pricing-table">
            <thead>
              <tr>
                <th>{t("pricing.customers.customer")}</th>
                <th>{t("pricing.customers.priceList")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.id}>
                  <td>
                    <Bdi>{nameOf(row.customer_code) ?? row.customer_code}</Bdi>
                  </td>
                  <td>
                    <Bdi>{row.price_list_code}</Bdi>
                  </td>
                  <td className="pricing-table__num">
                    <button
                      type="button"
                      className="btn btn--sm"
                      onClick={() => onRemove(row)}
                      aria-label={t("common.delete")}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Per-customer item overrides ───────────────────────────────────────────────────────────────────
function OverridesBlock({
  customers,
  items,
  t,
  toast,
}: {
  customers: Customer[];
  items: StockItem[];
  t: TFn;
  toast: Toast;
}) {
  const { data, loading, error, reload, mutate } = useAsync(listCustomerPrices, [], "pricing:customer-prices");
  const [customer, setCustomer] = useState("");
  const [sku, setSku] = useState("");
  const [price, setPrice] = useState("");
  const [minQty, setMinQty] = useState("");
  const [taxInclusive, setTaxInclusive] = useState(false);
  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");

  function onAdd(e: FormEvent) {
    e.preventDefault();
    const c = customer.trim();
    const minor = parseToMinor(price);
    if (!c || !sku || minor === null) {
      toast.show(t("pricing.customers.badInput"), "error");
      return;
    }
    const mq = minQty.trim() || "0";
    const from = validFrom || null;
    const to = validTo || null;
    const tax = taxInclusive;
    void optimisticCreate<CustomerItemPrice>({
      current: data ?? [],
      mutate,
      placeholder: (id) =>
        ({
          id,
          customer_code: c,
          item_sku: sku,
          uom: "unit",
          unit_price_minor: minor,
          tax_inclusive: tax,
          min_quantity: mq,
          valid_from: from,
          valid_to: to,
        }) as CustomerItemPrice,
      request: () =>
        addCustomerPrice({
          customer_code: c,
          item_sku: sku,
          unit_price_minor: minor,
          tax_inclusive: tax,
          min_quantity: mq,
          valid_from: from,
          valid_to: to,
        }),
      toast,
      success: t("pricing.toast.overrideAdded"),
    });
    setCustomer("");
    setSku("");
    setPrice("");
    setMinQty("");
    setTaxInclusive(false);
    setValidFrom("");
    setValidTo("");
  }

  function onRemove(row: CustomerItemPrice) {
    void runOptimistic<CustomerItemPrice[], void>({
      current: data ?? [],
      mutate,
      optimistic: (cur) => cur.filter((r) => r.id !== row.id),
      request: () => deleteCustomerPrice(row.id),
      toast,
      success: t("pricing.toast.overrideRemoved"),
    });
  }

  const nameOf = (code: string) => customers.find((c) => c.code === code)?.name;
  const validLabel = (row: CustomerItemPrice) => {
    if (!row.valid_from && !row.valid_to) return t("pricing.customers.always");
    return `${row.valid_from ?? "…"} → ${row.valid_to ?? "…"}`;
  };

  return (
    <div className="pricing-block">
      <h2 className="pricing-block__title">{t("pricing.customers.overrideTitle")}</h2>
      <p className="muted pricing-block__hint">{t("pricing.customers.overrideHint")}</p>

      <form className="card pricing-toolbar" onSubmit={onAdd}>
        <label className="pricing-field">
          <span>{t("pricing.customers.customer")}</span>
          <select value={customer} onChange={(e) => setCustomer(e.target.value)}>
            <option value="">—</option>
            {customers.map((c) => (
              <option key={c.code} value={c.code}>
                {c.code} · {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="pricing-field">
          <span>{t("pricing.detail.item")}</span>
          <select value={sku} onChange={(e) => setSku(e.target.value)}>
            <option value="">—</option>
            {items.map((it) => (
              <option key={it.sku} value={it.sku}>
                {it.sku} · {it.name}
              </option>
            ))}
          </select>
        </label>
        <label className="pricing-field">
          <span>{t("pricing.detail.unitPrice")}</span>
          <input
            className="latin"
            inputMode="decimal"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="0.00"
          />
        </label>
        <label className="pricing-field">
          <span>{t("pricing.detail.minQty")}</span>
          <input
            className="latin"
            inputMode="decimal"
            value={minQty}
            onChange={(e) => setMinQty(e.target.value)}
            placeholder="0"
          />
        </label>
        <label className="pricing-field">
          <span>{t("pricing.customers.validFrom")}</span>
          <input className="latin" type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
        </label>
        <label className="pricing-field">
          <span>{t("pricing.customers.validTo")}</span>
          <input className="latin" type="date" value={validTo} onChange={(e) => setValidTo(e.target.value)} />
        </label>
        <label className="pricing-field pricing-field--check">
          <input type="checkbox" checked={taxInclusive} onChange={(e) => setTaxInclusive(e.target.checked)} />
          <span>{t("pricing.customers.taxInclusive")}</span>
        </label>
        <button className="btn btn--primary" type="submit">
          {t("pricing.customers.addOverride")}
        </button>
      </form>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("pricing.customers.overrideEmpty")} hint={t("pricing.customers.overrideEmptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="card pricing-table-wrap">
          <table className="pricing-table">
            <thead>
              <tr>
                <th>{t("pricing.customers.customer")}</th>
                <th>{t("pricing.detail.item")}</th>
                <th className="pricing-table__num">{t("pricing.detail.minQty")}</th>
                <th className="pricing-table__num">{t("pricing.detail.unitPrice")}</th>
                <th>{t("pricing.customers.valid")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.id}>
                  <td>
                    <Bdi>{nameOf(row.customer_code) ?? row.customer_code}</Bdi>
                  </td>
                  <td>
                    <Bdi>{row.item_sku}</Bdi>
                  </td>
                  <td className="pricing-table__num">
                    <Bdi>{row.min_quantity}</Bdi>
                  </td>
                  <td className="pricing-table__num">
                    <Bdi>{formatMinor(row.unit_price_minor)}</Bdi>
                    {row.tax_inclusive && (
                      <span className="pricing-tag pricing-tag--inline">{t("pricing.list.taxInclusive")}</span>
                    )}
                  </td>
                  <td>
                    <Bdi>{validLabel(row)}</Bdi>
                  </td>
                  <td className="pricing-table__num">
                    <button
                      type="button"
                      className="btn btn--sm"
                      onClick={() => onRemove(row)}
                      aria-label={t("common.delete")}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
