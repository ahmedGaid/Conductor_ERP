import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import {
  addLine,
  deleteLine,
  getPriceList,
  listLines,
  updatePriceList,
  type PriceList,
  type PriceListLine,
} from "../../api/pricing";
import { listItems } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { EmptyState } from "../../components/EmptyState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate, runOptimistic } from "../../lib/optimistic";
import { formatMinor, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ImportDialog } from "../../components/ImportDialog";
import type { ImportFieldInfo } from "../../api/imports";
import "./pricing.css";

export function PriceListDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { id } = useParams<{ id: string }>();
  const listId = id as string;

  const { data: pl, mutate: mutateList } = useAsync<PriceList>(
    () => getPriceList(listId), [listId], `pricing:list:${listId}`,
  );
  const { data: lines, loading, error, reload, mutate } = useAsync(
    () => listLines(listId), [listId], `pricing:lines:${listId}`,
  );
  const { data: items } = useAsync(listItems, [], "inventory:items");

  const [sku, setSku] = useState("");
  const [price, setPrice] = useState("");
  const [minQty, setMinQty] = useState("");
  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");
  const [importOpen, setImportOpen] = useState(false);

  const importFields = useMemo<ImportFieldInfo[]>(() => [
    { name: "item_sku", label: t("pricing.detail.importField_item_sku"), required: true },
    { name: "unit_price", label: t("pricing.detail.importField_unit_price"), required: true },
    { name: "min_quantity", label: t("pricing.detail.importField_min_quantity") },
    { name: "uom", label: t("pricing.detail.importField_uom") },
  ], [t]);

  function patchList(changes: Partial<PriceList>) {
    if (!pl) return;
    void runOptimistic<PriceList, PriceList>({
      current: pl,
      mutate: mutateList,
      optimistic: (cur) => ({ ...cur, ...changes }),
      request: () => updatePriceList(listId, changes),
      settle: (_p, updated) => updated,
      toast,
      success: t("pricing.toast.updated"),
    });
  }

  function onAddLine(e: FormEvent) {
    e.preventDefault();
    const minor = parseToMinor(price);
    if (!sku || minor === null) {
      toast.show(t("pricing.detail.badInput"), "error");
      return;
    }
    const mq = minQty.trim() || "0";
    const from = validFrom || null;
    const to = validTo || null;
    void optimisticCreate<PriceListLine>({
      current: lines ?? [],
      mutate,
      placeholder: (lid) =>
        ({ id: lid, item_sku: sku, uom: "unit", unit_price_minor: minor, min_quantity: mq, valid_from: from, valid_to: to }) as PriceListLine,
      request: () => addLine(listId, { item_sku: sku, unit_price_minor: minor, min_quantity: mq, valid_from: from, valid_to: to }),
      toast,
      success: t("pricing.toast.priceAdded"),
    });
    setSku("");
    setPrice("");
    setMinQty("");
    setValidFrom("");
    setValidTo("");
  }

  function onDelete(line: PriceListLine) {
    void runOptimistic<PriceListLine[], void>({
      current: lines ?? [],
      mutate,
      optimistic: (cur) => cur.filter((l) => l.id !== line.id),
      request: () => deleteLine(line.id),
      toast,
      success: t("pricing.toast.priceRemoved"),
    });
  }

  const stockItems = (items ?? []).filter((i) => i.type === "stock");

  return (
    <section className="pricing-page">
      <div className="pricing-head">
        <Link to="/pricing" className="pricing-head__back">← {t("pricing.detail.back")}</Link>
        <div className="pricing-detail-head">
          <h1>{pl ? pl.name : t("pricing.title")}</h1>
          {pl && (
            <div className="pricing-toggles">
              <label className="pricing-toggle">
                <input type="checkbox" checked={pl.is_default} onChange={(e) => patchList({ is_default: e.target.checked })} />
                <span>{t("pricing.detail.defaultBadge")}</span>
              </label>
              <label className="pricing-toggle">
                <input type="checkbox" checked={pl.tax_inclusive} onChange={(e) => patchList({ tax_inclusive: e.target.checked })} />
                <span>{t("pricing.detail.taxInclusiveLabel")}</span>
              </label>
              <label className="pricing-toggle">
                <input type="checkbox" checked={pl.is_active} onChange={(e) => patchList({ is_active: e.target.checked })} />
                <span>{t("pricing.detail.activeLabel")}</span>
              </label>
            </div>
          )}
        </div>
      </div>

      <form className="card pricing-toolbar" onSubmit={onAddLine}>
        <label className="pricing-field">
          <span>{t("pricing.detail.item")}</span>
          <select value={sku} onChange={(e) => setSku(e.target.value)}>
            <option value="">—</option>
            {stockItems.map((it) => (
              <option key={it.sku} value={it.sku}>{it.sku} · {it.name}</option>
            ))}
          </select>
        </label>
        <label className="pricing-field">
          <span>{t("pricing.detail.unitPrice")}</span>
          <input className="latin" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="0.00" />
        </label>
        <label className="pricing-field">
          <span>{t("pricing.detail.minQty")}</span>
          <input className="latin" inputMode="decimal" value={minQty} onChange={(e) => setMinQty(e.target.value)} placeholder="0" />
        </label>
        <label className="pricing-field">
          <span>{t("pricing.customers.validFrom")}</span>
          <input className="latin" type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
        </label>
        <label className="pricing-field">
          <span>{t("pricing.customers.validTo")}</span>
          <input className="latin" type="date" value={validTo} onChange={(e) => setValidTo(e.target.value)} />
        </label>
        <button className="btn btn--primary" type="submit">{t("pricing.detail.addLine")}</button>
        <button type="button" className="btn btn--sm" onClick={() => setImportOpen(true)}>
          {t("pricing.detail.importBtn")}
        </button>
      </form>

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        basePath={`/pricing/price-lists/${listId}/lines`}
        title={t("import.pricingLines.title")}
        templateName={`price-lines-${pl?.code ?? "template"}.csv`}
        fields={importFields}
        onCommitted={() => { reload(); }}
      />

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {lines && lines.length === 0 && (
        <EmptyState title={t("pricing.detail.empty")} hint={t("pricing.detail.emptyHint")} />
      )}

      {lines && lines.length > 0 && (
        <div className="card pricing-table-wrap">
          <table className="pricing-table">
            <thead>
              <tr>
                <th>{t("pricing.detail.item")}</th>
                <th className="pricing-table__num">{t("pricing.detail.minQty")}</th>
                <th className="pricing-table__num">{t("pricing.detail.unitPrice")}</th>
                <th>{t("pricing.customers.valid")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.id}>
                  <td><Bdi>{l.item_sku}</Bdi></td>
                  <td className="pricing-table__num"><Bdi>{l.min_quantity}</Bdi></td>
                  <td className="pricing-table__num"><Bdi>{formatMinor(l.unit_price_minor, pl?.currency)}</Bdi></td>
                  <td>
                    <Bdi>
                      {!l.valid_from && !l.valid_to
                        ? t("pricing.customers.always")
                        : `${l.valid_from ?? "…"} → ${l.valid_to ?? "…"}`}
                    </Bdi>
                  </td>
                  <td className="pricing-table__num">
                    <button type="button" className="btn btn--sm" onClick={() => onDelete(l)} aria-label={t("common.delete")}>✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
