import { useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { extractDocument, type ExtractProposal } from "../../api/assistant";
import { createPurchaseOrder, createSupplier, listSuppliers, type NewPOLine } from "../../api/purchasing";
import { createItem, listItems, listWarehouses } from "../../api/inventory";
import { listTaxCodes } from "../../api/accounting";
import { NavIcon } from "../../app/icons";
import { useToast } from "../../app/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor, minorToAmount, parseToMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { ComboBox } from "../../components/ComboBox";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

// One editable review line: what the assistant read (kept for reference) + what will be ordered.
interface ReviewLine {
  extracted: string;
  item_sku: string;
  quantity: string;
  unit_cost: string;
}

const ACCEPT = "image/jpeg,image/png,image/webp,application/pdf";

function toReviewLines(proposal: ExtractProposal): ReviewLine[] {
  if (proposal.lines.length === 0) return [{ extracted: "", item_sku: "", quantity: "", unit_cost: "" }];
  return proposal.lines.map((l) => ({
    extracted: l.description,
    item_sku: l.matched_sku ?? "",
    quantity: l.quantity,
    unit_cost: l.unit_price_minor === null ? "" : minorToAmount(l.unit_price_minor),
  }));
}

export function ImportInvoicePage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: suppliers, mutate: mutateSuppliers } = useAsync(listSuppliers, [], "purchasing:suppliers");
  const { data: warehouses } = useAsync(listWarehouses, [], "inventory:warehouses");
  const { data: items, mutate: mutateItems } = useAsync(listItems, [], "inventory:items");
  const { data: taxCodes } = useAsync(listTaxCodes, [], "accounting:tax-codes");

  const [reading, setReading] = useState(false);
  const [proposal, setProposal] = useState<ExtractProposal | null>(null);
  const [supplier, setSupplier] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [taxCode, setTaxCode] = useState("");
  const [lines, setLines] = useState<ReviewLine[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Inline "the assistant read something we don't have yet" → create it here, prefilled, without
  // leaving the review: the new record is added to the list and selected in place.
  const [newSupplier, setNewSupplier] = useState<{ code: string; name: string } | null>(null);
  const [newItem, setNewItem] = useState<{ line: number; sku: string; name: string; uom: string } | null>(null);
  const [saving, setSaving] = useState(false);

  async function readFile(file: File) {
    setReading(true);
    setError(null);
    try {
      const result = await extractDocument(file);
      setProposal(result);
      setSupplier(result.supplier.matched_code ?? "");
      setLines(toReviewLines(result));
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setReading(false);
    }
  }

  function onPick(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) void readFile(file);
    e.target.value = ""; // same file can be picked again after a retry
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) void readFile(file);
  }

  function reset() {
    setProposal(null);
    setLines([]);
    setSupplier("");
    setError(null);
    setNewSupplier(null);
    setNewItem(null);
  }

  function setLine(i: number, patch: Partial<ReviewLine>) {
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  // Suggest an editable, unique-ish code from the current count — the user can override before saving.
  const suggestCode = (prefix: string, count: number) => `${prefix}-${String(count + 1).padStart(3, "0")}`;

  function openNewSupplier() {
    setNewSupplier({ code: suggestCode("SUP", (suppliers ?? []).length), name: proposal?.supplier.name ?? "" });
  }

  async function saveNewSupplier() {
    if (!newSupplier) return;
    const code = newSupplier.code.trim();
    const name = newSupplier.name.trim();
    if (!code || !name) return;
    setSaving(true);
    try {
      const created = await createSupplier({ code, name });
      mutateSuppliers([...(suppliers ?? []), created]);
      setSupplier(created.code);
      setNewSupplier(null);
      toast.show(t("purchasing.importInvoice.supplierCreated", { name: created.name }), "success");
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setSaving(false);
    }
  }

  function openNewItem(i: number) {
    setNewItem({ line: i, sku: suggestCode("ITM", (items ?? []).length), name: lines[i].extracted, uom: "unit" });
  }

  async function saveNewItem() {
    if (!newItem) return;
    const sku = newItem.sku.trim();
    const name = newItem.name.trim();
    if (!sku || !name) return;
    setSaving(true);
    try {
      const created = await createItem({ sku, name, uom: newItem.uom.trim() || "unit", type: "stock" });
      mutateItems([...(items ?? []), created]);
      setLine(newItem.line, { item_sku: created.sku });
      setNewItem(null);
      toast.show(t("purchasing.importInvoice.itemCreated", { name: created.name }), "success");
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setSaving(false);
    }
  }

  const subtotal = lines.reduce((s, l) => {
    const qty = Number(l.quantity) || 0;
    const cost = parseToMinor(l.unit_cost) ?? 0;
    return s + Math.round(qty * cost);
  }, 0);
  const taxRateBps = (taxCodes ?? []).find((c) => c.code === taxCode)?.rate_bps ?? 0;
  const vat = Math.round((subtotal * taxRateBps) / 10000);
  const extractedTotal = proposal?.invoice.total_minor ?? null;
  const totalsDiffer = extractedTotal !== null && subtotal + vat !== extractedTotal;

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
      payloadLines.push({ item_sku: l.item_sku, quantity: l.quantity, unit_cost: cost, description: l.extracted });
    }
    if (payloadLines.length === 0) {
      setError(t("purchasing.newOrder.needLine"));
      return;
    }
    setBusy(true);
    try {
      const order = await createPurchaseOrder({
        supplier_code: supplier,
        warehouse_code: warehouse,
        tax_code: taxCode,
        notes: proposal?.invoice.number ? `${t("purchasing.importInvoice.noteRef")} ${proposal.invoice.number}` : "",
        lines: payloadLines,
      });
      navigate(`/purchasing/orders/${order.id}`, { state: { feedback: "created" } });
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

      {/* State 1 — upload (the designed empty state: one job, one action) */}
      {!proposal && !reading && (
        <div
          className="card pur-import-drop"
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
        >
          <span className="pur-import-drop__icon" aria-hidden="true">
            <NavIcon name="sparkle" />
          </span>
          <p className="pur-import-drop__title">{t("purchasing.importInvoice.dropTitle")}</p>
          <p className="pur-import-drop__hint">{t("purchasing.importInvoice.dropHint")}</p>
          <button type="button" className="btn btn--primary" onClick={() => fileRef.current?.click()}>
            {t("purchasing.importInvoice.choose")}
          </button>
          <p className="pur-import-drop__note">{t("purchasing.importInvoice.aiNote")}</p>
          <input ref={fileRef} type="file" accept={ACCEPT} onChange={onPick} hidden />
        </div>
      )}

      {/* State 2 — the assistant is reading (settled, no spinner theatrics) */}
      {reading && (
        <div className="card pur-import-drop" aria-busy="true">
          <span className="pur-import-drop__icon" aria-hidden="true">
            <NavIcon name="sparkle" />
          </span>
          <p className="pur-import-drop__title">{t("purchasing.importInvoice.reading")}</p>
          <p className="pur-import-drop__hint">{t("purchasing.importInvoice.readingHint")}</p>
          <div className="pur-import-progress" />
        </div>
      )}

      {/* State 3 — couldn't read it (designed, blame-free, with a way forward) */}
      {proposal && !proposal.readable && !reading && (
        <div className="card pur-import-drop">
          <span className="pur-import-drop__icon" aria-hidden="true">
            <NavIcon name="info" />
          </span>
          <p className="pur-import-drop__title">{t("purchasing.importInvoice.unreadableTitle")}</p>
          <p className="pur-import-drop__hint">{t("purchasing.importInvoice.unreadableHint")}</p>
          {proposal.issues.length > 0 && (
            <ul className="pur-import-issues">
              {proposal.issues.map((issue, i) => (
                <li key={i}>{issue}</li>
              ))}
            </ul>
          )}
          <button type="button" className="btn btn--primary" onClick={reset}>
            {t("purchasing.importInvoice.tryAnother")}
          </button>
        </div>
      )}

      {/* State 4 — review: extracted vs matched, everything editable, user posts */}
      {proposal && proposal.readable && !reading && (
        <form className="card pur-page" onSubmit={onSubmit}>
          <div className="pur-import-review-head">
            <h2 className="pur-import-review-head__title">{t("purchasing.importInvoice.reviewTitle")}</h2>
            <p className="pur-import-review-head__meta">
              <NavIcon name="sparkle" />
              {t("purchasing.importInvoice.confidence")}:{" "}
              {t(`purchasing.importInvoice.confidenceLevel.${proposal.confidence}`)}
              {proposal.invoice.number && (
                <>
                  {" · "}
                  {t("purchasing.importInvoice.invoiceNumber")} <Bdi>{proposal.invoice.number}</Bdi>
                </>
              )}
              {proposal.invoice.date && (
                <>
                  {" · "}
                  <Bdi>{proposal.invoice.date}</Bdi>
                </>
              )}
            </p>
          </div>

          {proposal.issues.length > 0 && (
            <div className="pur-import-issues-card">
              <p className="pur-import-issues-card__title">
                <NavIcon name="info" /> {t("purchasing.importInvoice.issuesTitle")}
              </p>
              <ul className="pur-import-issues">
                {proposal.issues.map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="pur-toolbar">
            <label className="pur-field">
              <span>{t("purchasing.orders.supplier")}</span>
              <ComboBox
                value={supplier}
                onChange={setSupplier}
                placeholder={t("common.selectField", { field: t("purchasing.orders.supplier") })}
                options={(suppliers ?? []).map((s) => ({ value: s.code, label: `${s.code} · ${s.name}` }))}
              />
              {proposal.supplier.name && (
                <span className="pur-import-extracted">
                  {t("purchasing.importInvoice.extractedSupplier")}: <Bdi>{proposal.supplier.name}</Bdi>
                  {proposal.supplier.tax_id && (
                    <>
                      {" · "}
                      {t("purchasing.importInvoice.taxId")} <Bdi>{proposal.supplier.tax_id}</Bdi>
                    </>
                  )}
                </span>
              )}
              {!supplier && !newSupplier && (
                <div className="pur-import-suggest">
                  <span className="pur-import-extracted">{t("purchasing.importInvoice.noSupplierMatch")}</span>
                  {proposal.supplier.name && (
                    <button type="button" className="btn btn--sm" onClick={openNewSupplier}>
                      <NavIcon name="plus" />{" "}
                      {t("purchasing.importInvoice.createSupplier", { name: proposal.supplier.name })}
                    </button>
                  )}
                </div>
              )}
              {newSupplier && (
                <div className="pur-import-create">
                  <div className="pur-import-create__fields">
                    <label className="pur-field">
                      <span>{t("purchasing.importInvoice.codeLabel")}</span>
                      <input
                        className="latin"
                        value={newSupplier.code}
                        onChange={(e) => setNewSupplier({ ...newSupplier, code: e.target.value })}
                      />
                    </label>
                    <label className="pur-field">
                      <span>{t("purchasing.importInvoice.nameLabel")}</span>
                      <input
                        value={newSupplier.name}
                        onChange={(e) => setNewSupplier({ ...newSupplier, name: e.target.value })}
                      />
                    </label>
                  </div>
                  <div className="pur-import-create__actions">
                    <button type="button" className="btn btn--sm" onClick={() => setNewSupplier(null)}>
                      {t("common.cancel")}
                    </button>
                    <button type="button" className="btn btn--sm btn--primary" onClick={saveNewSupplier} disabled={saving}>
                      {t("purchasing.importInvoice.confirmCreate")}
                    </button>
                  </div>
                </div>
              )}
            </label>
            <label className="pur-field">
              <span>{t("inventory.warehouse.label")}</span>
              <ComboBox
                value={warehouse}
                onChange={setWarehouse}
                placeholder={t("common.selectField", { field: t("inventory.warehouse.label") })}
                options={(warehouses ?? []).map((w) => ({ value: w.code, label: `${w.code} · ${w.name}` }))}
              />
            </label>
            <label className="pur-field">
              <span>{t("purchasing.newOrder.taxCode")}</span>
              <select value={taxCode} onChange={(e) => setTaxCode(e.target.value)}>
                <option value="">{t("purchasing.newOrder.noTax")}</option>
                {(taxCodes ?? []).map((c) => (
                  <option key={c.code} value={c.code}>{c.code} · {c.name}</option>
                ))}
              </select>
              {(proposal.invoice.vat_minor ?? 0) > 0 && (
                <span className="pur-import-extracted">
                  {t("purchasing.importInvoice.vatOnInvoice")}: <Bdi>{formatMinor(proposal.invoice.vat_minor!)}</Bdi>
                </span>
              )}
            </label>
          </div>

          <div className="pur-table-wrap">
            <table className="pur-table pur-import-table">
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
                        <ComboBox
                          value={l.item_sku}
                          onChange={(v) => setLine(i, { item_sku: v })}
                          placeholder={t("purchasing.importInvoice.noItemMatch")}
                          options={stockItems.map((it) => ({ value: it.sku, label: `${it.sku} · ${it.name}` }))}
                        />
                        {l.extracted && (
                          <span className="pur-import-extracted">
                            {t("purchasing.importInvoice.extractedLine")}: <Bdi>{l.extracted}</Bdi>
                          </span>
                        )}
                        {!l.item_sku && l.extracted && newItem?.line !== i && (
                          <button type="button" className="btn btn--sm pur-import-suggest__btn" onClick={() => openNewItem(i)}>
                            <NavIcon name="plus" /> {t("purchasing.importInvoice.createItem", { name: l.extracted })}
                          </button>
                        )}
                        {newItem?.line === i && (
                          <div className="pur-import-create">
                            <div className="pur-import-create__fields">
                              <label className="pur-field">
                                <span>{t("purchasing.importInvoice.codeLabel")}</span>
                                <input
                                  className="latin"
                                  value={newItem.sku}
                                  onChange={(e) => setNewItem({ ...newItem, sku: e.target.value })}
                                />
                              </label>
                              <label className="pur-field">
                                <span>{t("purchasing.importInvoice.nameLabel")}</span>
                                <input
                                  value={newItem.name}
                                  onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                                />
                              </label>
                              <label className="pur-field pur-import-create__uom">
                                <span>{t("purchasing.importInvoice.uomLabel")}</span>
                                <input
                                  value={newItem.uom}
                                  onChange={(e) => setNewItem({ ...newItem, uom: e.target.value })}
                                />
                              </label>
                            </div>
                            <div className="pur-import-create__actions">
                              <button type="button" className="btn btn--sm" onClick={() => setNewItem(null)}>
                                {t("common.cancel")}
                              </button>
                              <button type="button" className="btn btn--sm btn--primary" onClick={saveNewItem} disabled={saving}>
                                {t("purchasing.importInvoice.confirmCreate")}
                              </button>
                            </div>
                          </div>
                        )}
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
                  <td colSpan={3}>{t("sales.newOrder.subtotal")}</td>
                  <td className="pur-table__num"><Bdi>{formatMinor(subtotal)}</Bdi></td>
                  <td />
                </tr>
                {vat > 0 && (
                  <tr>
                    <td colSpan={3}>{t("purchasing.detail.vat")}</td>
                    <td className="pur-table__num"><Bdi>{formatMinor(vat)}</Bdi></td>
                    <td />
                  </tr>
                )}
                <tr>
                  <td colSpan={3}>{t("accounting.entry.totals")}</td>
                  <td className="pur-table__num"><Bdi>{formatMinor(subtotal + vat)}</Bdi></td>
                  <td />
                </tr>
                {extractedTotal !== null && (
                  <tr>
                    <td colSpan={3}>{t("purchasing.importInvoice.invoiceTotals")}</td>
                    <td className="pur-table__num"><Bdi>{formatMinor(extractedTotal)}</Bdi></td>
                    <td />
                  </tr>
                )}
              </tfoot>
            </table>
          </div>

          {totalsDiffer && (
            <p className="pur-import-mismatch">
              <NavIcon name="info" /> {t("purchasing.importInvoice.totalsMismatch")}
            </p>
          )}

          <div className="pur-actions">
            <button type="button" className="btn btn--sm" onClick={() => setLines((ls) => [...ls, { extracted: "", item_sku: "", quantity: "", unit_cost: "" }])}>
              {t("purchasing.newOrder.addLine")}
            </button>
            <button type="button" className="btn btn--sm" onClick={reset}>
              {t("purchasing.importInvoice.startOver")}
            </button>
            <button type="submit" className="btn btn--primary" disabled={busy}>
              {t("purchasing.importInvoice.createDraft")}
            </button>
          </div>
          {error && <p className="error-text">{error}</p>}
        </form>
      )}
    </section>
  );
}
