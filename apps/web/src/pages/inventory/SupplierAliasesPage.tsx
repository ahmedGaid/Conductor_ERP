import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  deleteSupplierAlias,
  listItems,
  listSupplierAliases,
  repointSupplierAlias,
  type SupplierAlias,
} from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { useListPageActions } from "../../hooks/useListPageActions";
import { type CsvColumn } from "../../lib/csvExport";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { ComboBox, type ComboBoxOption } from "../../components/ComboBox";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { EntityLink } from "../../components/EntityLink";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { FilterBar } from "../../components/FilterBar";
import { ListSkeleton } from "../../components/ListSkeleton";
import { RowActions } from "../../components/RowActions";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

/**
 * Supplier-item aliases: the memory of the import learning loop. Each row is one supplier's own
 * code/name for an item, mapped to the canonical Conductor item. This screen makes that memory
 * visible so a human can trust it — and correct it: re-point a mis-learned mapping to the right
 * item (inline, via a searchable picker), or delete one so the next document re-learns it. Aliases
 * are learned during ingestion, never typed here, so there is no create form.
 */
export function SupplierAliasesPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(
    () => listSupplierAliases(),
    [],
    "inventory:supplierAliases",
  );
  // Items power the re-point picker; a plain list load, cached alongside the Items page's.
  const { data: items } = useAsync(listItems, [], "inventory:items");

  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editSku, setEditSku] = useState("");
  const [deleting, setDeleting] = useState<SupplierAlias | null>(null);

  const fields = useMemo<FilterField<SupplierAlias>[]>(
    () => [
      { key: "supplier_code", label: t("inventory.alias.supplier"), type: "text", accessor: (a) => a.supplier_code },
      { key: "supplier_item_code", label: t("inventory.alias.supplierItemCode"), type: "text", accessor: (a) => a.supplier_item_code },
      { key: "supplier_item_name", label: t("inventory.alias.supplierItemName"), type: "text", accessor: (a) => a.supplier_item_name },
      { key: "item_sku", label: t("inventory.alias.canonicalItem"), type: "text", accessor: (a) => `${a.item_sku} ${a.item_name}` },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((a) => matchesAllFilters(a, fields, filters)) : data),
    [data, fields, filters],
  );

  const csvColumns = useMemo<CsvColumn<SupplierAlias>[]>(
    () => [
      { header: t("inventory.alias.supplier"), accessor: (a) => a.supplier_code },
      { header: t("inventory.alias.supplierItemCode"), accessor: (a) => a.supplier_item_code },
      { header: t("inventory.alias.supplierItemName"), accessor: (a) => a.supplier_item_name },
      { header: t("inventory.item.sku"), accessor: (a) => a.item_sku },
      { header: t("inventory.item.name"), accessor: (a) => a.item_name },
      { header: t("inventory.alias.source"), accessor: (a) => t(`inventory.alias.sources.${a.source}`) },
    ],
    [t],
  );
  useListPageActions({ rows: filtered, columns: csvColumns, filename: "supplier-aliases" });

  const itemOptions = useMemo<ComboBoxOption[]>(
    () => (items ?? []).map((i) => ({ value: i.sku, label: `${i.sku} — ${i.name}` })),
    [items],
  );

  function startEdit(alias: SupplierAlias) {
    setEditingId(alias.id);
    setEditSku(alias.item_sku);
  }
  function cancelEdit() {
    setEditingId(null);
    setEditSku("");
  }

  function onDelete(alias: SupplierAlias) {
    void runOptimistic<SupplierAlias[], void>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows.filter((r) => r.id !== alias.id),
      request: () => deleteSupplierAlias(alias.id),
      toast,
      success: t("inventory.alias.toast.deleted"),
    });
  }

  function saveRepoint(alias: SupplierAlias) {
    const sku = editSku;
    const name = itemOptions.find((o) => o.value === sku)?.label.split(" — ").slice(1).join(" — ") ?? sku;
    cancelEdit();
    if (sku === alias.item_sku) return;
    void runOptimistic<SupplierAlias[], SupplierAlias>({
      current: data ?? [],
      mutate,
      optimistic: (rows) =>
        rows.map((r) => (r.id === alias.id ? { ...r, item_sku: sku, item_name: name, source: "manual" } : r)),
      request: () => repointSupplierAlias(alias.id, sku),
      settle: (rows, updated) => rows.map((r) => (r.id === updated.id ? updated : r)),
      toast,
      success: t("inventory.alias.toast.repointed"),
    });
  }

  return (
    <section className="inv-page">
      <InventoryNav />

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("inventory.alias.empty")} hint={t("inventory.alias.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="inv-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState
          title={t("filter.noMatch")}
          hint={t("filter.noMatchHint")}
          action={{ label: t("filter.clearAll"), onClick: () => setFilters([]) }}
        />
      )}

      {filtered && filtered.length > 0 && (
        <div className="card inv-table-wrap">
          <table className="inv-table">
            <thead>
              <tr>
                <th>{t("inventory.alias.supplier")}</th>
                <th>{t("inventory.alias.supplierItemCode")}</th>
                <th>{t("inventory.alias.supplierItemName")}</th>
                <th>{t("inventory.alias.canonicalItem")}</th>
                <th>{t("inventory.alias.source")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((a) => {
                const editing = editingId === a.id;
                return (
                  <tr key={a.id} data-selected={editing ? "true" : undefined}>
                    <td className="latin">{a.supplier_code}</td>
                    <td className="latin">
                      {a.supplier_item_code || <span className="inv-muted">—</span>}
                    </td>
                    <td>{a.supplier_item_name || <span className="inv-muted">—</span>}</td>
                    <td>
                      {editing ? (
                        <ComboBox
                          options={itemOptions}
                          value={editSku}
                          onChange={setEditSku}
                          placeholder={t("inventory.alias.chooseItem")}
                          aria-label={t("inventory.alias.chooseItem")}
                        />
                      ) : (
                        <>
                          <EntityLink type="item" value={a.item_sku} />
                          <span className="inv-muted"> — {a.item_name}</span>
                        </>
                      )}
                    </td>
                    <td>{t(`inventory.alias.sources.${a.source}`)}</td>
                    <td>
                      {editing ? (
                        <div className="row-actions" role="group" aria-label={t("common.actions")}>
                          <button
                            type="button"
                            className="btn btn--sm btn--primary"
                            disabled={editSku === "" || editSku === a.item_sku}
                            onClick={() => saveRepoint(a)}
                          >
                            {t("inventory.alias.save")}
                          </button>
                          <button type="button" className="btn btn--sm btn--ghost" onClick={cancelEdit}>
                            {t("common.cancel")}
                          </button>
                        </div>
                      ) : (
                        <RowActions label={t("common.actions")}>
                          <button type="button" className="btn btn--sm" onClick={() => startEdit(a)}>
                            {t("inventory.alias.repoint")}
                          </button>
                          <button type="button" className="btn btn--sm" onClick={() => setDeleting(a)}>
                            {t("inventory.alias.delete")}
                          </button>
                        </RowActions>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        open={deleting !== null}
        danger
        title={t("inventory.alias.deleteTitle")}
        body={
          deleting
            ? t("inventory.alias.deleteBody", {
                supplier: deleting.supplier_code,
                ref: deleting.supplier_item_code || deleting.supplier_item_name,
              })
            : undefined
        }
        confirmLabel={t("inventory.alias.delete")}
        onConfirm={() => {
          if (deleting) onDelete(deleting);
          setDeleting(null);
        }}
        onClose={() => setDeleting(null)}
      />
    </section>
  );
}

export default SupplierAliasesPage;
