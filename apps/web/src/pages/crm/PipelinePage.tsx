import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../../app/icons";
import { Link } from "react-router-dom";

import {
  advanceStage,
  createOpportunity,
  getOpportunity,
  listOpportunities,
  type NewOppLine,
  type OppStage,
  type Opportunity,
} from "../../api/crm";
import { listCustomers } from "../../api/sales";
import { listItems, listWarehouses } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { Badge } from "../../components/Badge";
import { crmTone } from "../../lib/statusTone";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { useUndoableAction } from "../../lib/useUndoableAction";
import { prefetch } from "../../lib/prefetch";
import { formatMinor, parseToMinor } from "../../lib/money";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { Bdi } from "../../components/Bdi";
import { ComboBox } from "../../components/ComboBox";
import { EmptyState } from "../../components/EmptyState";
import { CrmNav } from "./CrmNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./crm.css";

interface DraftLine {
  item_sku: string;
  quantity: string;
  unit_price: string;
}

const emptyLine = (): DraftLine => ({ item_sku: "", quantity: "", unit_price: "" });

// Stages an opportunity can move between freely from the list — mirrors the detail page's
// undo-not-confirm "advance" action. Won/lost are a separate, consequential flow (spawns a sales
// order / closes the deal for good) and are never reachable from this quiet inline control.
const OPEN_STAGES: OppStage[] = ["qualifying", "proposal", "negotiation"];

export function PipelinePage() {
  const { t } = useTranslation();
  const toast = useToast();
  const undoable = useUndoableAction();
  const { data, loading, error, reload, mutate } = useAsync(() => listOpportunities(), [], "crm:opportunities");
  const [editingStageId, setEditingStageId] = useState<string | null>(null);

  // Same optimistic-flip + undo-window contract as OpportunityDetailPage's `advance`, applied to
  // one row of the list array instead of a single-record cache entry.
  function advanceRow(o: Opportunity, next: OppStage) {
    if (!data) return;
    const snapshot = data;
    mutate(snapshot.map((row) => (row.id === o.id ? { ...row, stage: next } : row)));
    void undoable<Opportunity>({
      perform: () => advanceStage(o.id, next),
      undo: async () => {
        await advanceStage(o.id, o.stage);
      },
      message: t("crm.toast.stageAdvanced", { stage: t(`crm.stage.${next}`) }),
      onUndone: () => mutate(snapshot),
    });
  }
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

  // The new-opportunity form has line items (forms keep their controls) — no bar primary, just
  // print + CSV of the pipeline table below.
  const csvColumns = useMemo<CsvColumn<Opportunity>[]>(
    () => [
      { header: t("crm.opp.number"), accessor: (o) => o.number },
      { header: t("crm.opp.name"), accessor: (o) => o.name },
      { header: t("crm.opp.stage"), accessor: (o) => t(`crm.stage.${o.stage}`) },
      { header: t("crm.opp.amount"), accessor: (o) => formatMinor(o.amount_minor, o.currency) },
      { header: t("crm.opp.weighted"), accessor: (o) => formatMinor(o.weighted_minor, o.currency) },
    ],
    [t],
  );
  useListPageActions({ rows: data, columns: csvColumns, filename: "pipeline" });

  // Multi-select for bulk CSV export (stage moves stay on the opportunity detail page; no list-level
  // keyboard nav here, so mouse/Shift-range/⌘A/Esc drive selection).
  const selection = useRowSelection<Opportunity>({
    items: data ?? [],
    getItemId: (o) => o.id,
  });

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
            <ComboBox
              value={customer}
              onChange={setCustomer}
              placeholder={t("common.selectField", { field: t("crm.opp.customer") })}
              options={(customers ?? []).map((c) => ({ value: c.code, label: `${c.code} · ${c.name}` }))}
            />
          </label>
          <label className="crm-field">
            <span>{t("inventory.warehouse.label")}</span>
            <ComboBox
              value={warehouse}
              onChange={setWarehouse}
              placeholder={t("common.selectField", { field: t("inventory.warehouse.label") })}
              options={(warehouses ?? []).map((w) => ({ value: w.code, label: `${w.code} · ${w.name}` }))}
            />
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
                      <ComboBox
                        value={l.item_sku}
                        onChange={(v) => setLine(i, { item_sku: v })}
                        placeholder={t("common.selectField", { field: t("sales.newOrder.item") })}
                        options={stockItems.map((it) => ({ value: it.sku, label: `${it.sku} · ${it.name}` }))}
                      />
                    </td>
                    <td className="crm-table__num">
                      <input className="latin" inputMode="decimal" value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} />
                    </td>
                    <td className="crm-table__num">
                      <input className="latin" inputMode="decimal" value={l.unit_price} onChange={(e) => setLine(i, { unit_price: e.target.value })} placeholder="0.00" />
                    </td>
                    <td className="crm-table__num"><Bdi>{formatMinor(lineTotal)}</Bdi></td>
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
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <EmptyState title={t("crm.pipeline.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="card crm-table-wrap">
          <table className="crm-table">
            <thead>
              <tr>
                <SelectAllCell
                  className="crm-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("crm.opp.number")}</th>
                <th>{t("crm.opp.name")}</th>
                <th>{t("crm.opp.stage")}</th>
                <th className="crm-table__num">{t("crm.opp.amount")}</th>
                <th className="crm-table__num">{t("crm.opp.weighted")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((o: Opportunity, i) => (
                <tr key={o.id} data-selected={selection.isSelected(o.id) ? "true" : undefined} aria-selected={selection.isSelected(o.id)}>
                  <SelectRowCell
                    className="crm-table__select"
                    checked={selection.isSelected(o.id)}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
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
                    {editingStageId === o.id ? (
                      <select
                        className="crm-stage-edit"
                        autoFocus
                        aria-label={t("common.editField", { field: t("crm.opp.stage") })}
                        value={o.stage}
                        onChange={(e) => {
                          const next = e.target.value as OppStage;
                          setEditingStageId(null);
                          if (next !== o.stage) advanceRow(o, next);
                        }}
                        onBlur={() => setEditingStageId(null)}
                        onKeyDown={(e) => {
                          if (e.key === "Escape") {
                            e.stopPropagation();
                            setEditingStageId(null);
                          }
                        }}
                      >
                        {OPEN_STAGES.map((s) => (
                          <option key={s} value={s}>{t(`crm.stage.${s}`)}</option>
                        ))}
                      </select>
                    ) : (
                      <button
                        type="button"
                        className="crm-stage-cell"
                        onClick={() => {
                          if (OPEN_STAGES.includes(o.stage)) setEditingStageId(o.id);
                          else toast.show(t("crm.opp.stageClosed"), "info");
                        }}
                      >
                        <Badge tone={crmTone(o.stage)}>{t(`crm.stage.${o.stage}`)}</Badge>
                      </button>
                    )}
                  </td>
                  <td className="crm-table__num"><Bdi>{formatMinor(o.amount_minor, o.currency)}</Bdi></td>
                  <td className="crm-table__num muted"><Bdi>{formatMinor(o.weighted_minor, o.currency)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("pipeline-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
