import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { createItem, listItems, type Item, type ItemType } from "../../api/inventory";
import { listCustomFieldDefs } from "../../api/customFields";
import { buildCustomData, formatCustomFieldValue, validateCustomFieldValues, type CustomFieldValues } from "../../lib/customFields";
import { CustomFieldsForm } from "../../components/CustomFieldsForm";
import { useAsync } from "../../hooks/useAsync";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { useFormKeys } from "../../hooks/useFormKeys";
import { useDraftRecovery } from "../../hooks/useDraftRecovery";
import { DraftRecoveryBanner } from "../../components/DraftRecoveryBanner";
import { DraftStatusIndicator } from "../../components/DraftStatusIndicator";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { usePrefill } from "../../lib/usePrefill";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { matchesAllFilters, filtersFromParams, type ActiveFilter, type FilterField } from "../../lib/filters";
import { EntityLink } from "../../components/EntityLink";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
import { RowActions } from "../../components/RowActions";
import { ImportDialog } from "../../components/ImportDialog";
import type { ImportFieldInfo } from "../../api/imports";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { InventoryNav } from "./InventoryNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import { useSetHelpSignals } from "../../help/HelpSignalsContext";
import "./inventory.css";

const ITEM_TYPES: ItemType[] = ["stock", "service"];

// The shape autosaved as a draft. Its baseline is the form's untouched state (uom/type carry
// defaults), so an empty form is never offered back as recoverable work.
interface ItemDraft {
  sku: string;
  name: string;
  uom: string;
  type: ItemType;
  custom: CustomFieldValues;
}

const EMPTY_ITEM_DRAFT: ItemDraft = { sku: "", name: "", uom: "unit", type: "stock", custom: {} };

export function ItemsPage() {
  const { t, i18n } = useTranslation();
  const isArabic = i18n.resolvedLanguage?.startsWith("ar") ?? true;
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(listItems, [], "inventory:items");
  const { data: customFieldDefs } = useAsync(
    () => listCustomFieldDefs("inventory.item"),
    [],
    "settings:customFields:inventory.item",
  );
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState<string>(ALL_TAB);

  const fields = useMemo<FilterField<Item>[]>(
    () => [
      { key: "sku", label: t("inventory.item.sku"), type: "text", accessor: (i) => i.sku },
      { key: "name", label: t("inventory.item.name"), type: "text", accessor: (i) => i.name },
      {
        key: "type",
        label: t("inventory.item.type"),
        type: "select",
        options: ITEM_TYPES.map((ty) => ({ value: ty, label: t(`inventory.types.${ty}`) })),
        accessor: (i) => i.type,
      },
    ],
    [t],
  );

  // Seed chips from the URL so a drill-in link opens pre-filtered; the saved-views hook then keeps
  // the chips and the URL in step.
  const [filters, setFilters] = useState<ActiveFilter[]>(() => filtersFromParams(searchParams, fields));
  const savedViews = useSavedViews({ listKey: "inventory:items", fields, filters, setFilters });

  const filtered = useMemo(
    () => (data ? data.filter((i) => matchesAllFilters(i, fields, filters)) : data),
    [data, fields, filters],
  );

  const typeTabs = useMemo(
    () => ITEM_TYPES.map((ty) => ({ value: ty, label: t(`inventory.types.${ty}`) })),
    [t],
  );
  const visible = useMemo(
    () => (filtered ? (tab === ALL_TAB ? filtered : filtered.filter((i) => i.type === tab)) : filtered),
    [filtered, tab],
  );

  // j/k move a row highlight, Enter/o opens the item detail page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<Item>({
    items: visible ?? [],
    onOpen: (it) => navigate(`/inventory/items/${encodeURIComponent(it.sku)}`),
    persistKey: "inventory:items",
    getItemId: (it) => it.id,
  });

  // Multi-select for bulk CSV export of the selection (no other bulk verb applies to items).
  const selection = useRowSelection<Item>({
    items: visible ?? [],
    getItemId: (it) => it.id,
    activeIndex: active,
  });

  // Add is a form (forms keep their controls) — no bar primary, just print + CSV.
  const csvColumns = useMemo<CsvColumn<Item>[]>(
    () => [
      { header: t("inventory.item.sku"), accessor: (i) => i.sku },
      { header: t("inventory.item.name"), accessor: (i) => i.name },
      { header: t("inventory.item.uom"), accessor: (i) => i.uom },
      { header: t("inventory.item.type"), accessor: (i) => t(`inventory.types.${i.type}`) },
    ],
    [t],
  );
  useListPageActions({ rows: visible, columns: csvColumns, filename: "items" });

  // Assistant deep links land here with the extracted values (?prefill=…) — additive only.
  const prefill = usePrefill(["sku", "name"]);
  const [sku, setSku] = useState(prefill.sku ?? "");
  const [name, setName] = useState(prefill.name ?? "");
  const [uom, setUom] = useState("unit");
  const [type, setType] = useState<ItemType>("stock");
  const [importOpen, setImportOpen] = useState(false);
  const [customValues, setCustomValues] = useState<CustomFieldValues>({});
  const [customErrors, setCustomErrors] = useState<Record<string, string>>({});
  const [showForm, setShowForm] = useState(() => !!(prefill.sku || prefill.name));

  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef, onCancel: () => setShowForm(false) });

  // Autosave the half-typed item so closing the tab (or a crash) doesn't lose it.
  const draft = useMemo<ItemDraft>(
    () => ({ sku, name, uom, type, custom: customValues }),
    [sku, name, uom, type, customValues],
  );
  const recovery = useDraftRecovery<ItemDraft>({
    workflowKey: "inventory.item.create",
    entityType: "item",
    value: draft,
    baseline: EMPTY_ITEM_DRAFT,
    schemaVersion: 1,
  });

  function applyDraft(d: ItemDraft) {
    setSku(d.sku ?? "");
    setName(d.name ?? "");
    setUom(d.uom ?? "unit");
    setType(d.type ?? "stock");
    setCustomValues(d.custom ?? {});
    setShowForm(true);
  }

  // Publish the page's live facts for the Help drawer's Live tab.
  useSetHelpSignals({
    skuSet: sku.trim() !== "",
    nameSet: name.trim() !== "",
    itemCount: (data ?? []).length,
  });

  const importFields = useMemo<ImportFieldInfo[]>(
    () => [
      { name: "sku", label: t("inventory.item.sku"), required: true },
      { name: "name", label: t("inventory.item.name"), required: true },
      { name: "category_code", label: t("inventory.item.category") },
      { name: "uom", label: t("inventory.item.uom") },
      { name: "type", label: t("inventory.item.type") },
      { name: "reorder_point", label: t("inventory.item.reorderPoint") },
      { name: "is_active", label: t("inventory.item.active") },
    ],
    [t],
  );

  // Optimistic create: show the new item row instantly and clear the form for the next entry; the
  // server row replaces the placeholder on settle, or it rolls back + toasts.
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const s = sku.trim();
    const n = name.trim();
    if (!s || !n) return;
    const defs = customFieldDefs ?? [];
    const errors = validateCustomFieldValues(defs, customValues);
    if (Object.keys(errors).length > 0) {
      setCustomErrors(errors);
      return;
    }
    setCustomErrors({});
    const u = uom.trim() || "unit";
    const custom_data = buildCustomData(defs, customValues);
    void optimisticCreate<Item>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, sku: s, name: n, uom: u, type, custom_data }) as Item,
      request: () => createItem({ sku: s, name: n, uom: u, type, custom_data }),
      toast,
      success: t("inventory.toast.itemCreated"),
    }).then((created) => {
      // The workflow finished — the draft must not come back on the next visit.
      void recovery.complete(created ? String(created.id) : undefined);
    });
    setSku("");
    setName("");
    setCustomValues({});
    setShowForm(false);
  }

  return (
    <section className="inv-page">
      <InventoryNav />

      <div className="inv-page-actions">
        <button type="button" className="btn btn--sm" onClick={() => setImportOpen(true)}>
          {t("import.action")}
        </button>
        {!showForm && (
          <button type="button" className="btn btn--sm btn--primary" onClick={() => setShowForm(true)}>
            {t("inventory.item.add")}
          </button>
        )}
      </div>

      {recovery.recoverable && (
        <DraftRecoveryBanner
          entityLabel={t("drafts.workflow.inventory.item.create")}
          lastActiveAt={recovery.recoverable.lastActiveAt}
          onContinue={() => {
            const payload = recovery.recover();
            if (payload) applyDraft(payload);
          }}
          onDiscard={() => void recovery.discard()}
        />
      )}

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        basePath="/inventory/items"
        title={t("import.items.title")}
        templateName="items-template.csv"
        fields={importFields}
        onCommitted={() => reload()}
      />

      {showForm && (
      <form ref={formRef} className="card inv-toolbar" onSubmit={onSubmit}>
        <label className="inv-field">
          <span>{t("inventory.item.sku")}</span>
          <input className="latin" value={sku} onChange={(e) => setSku(e.target.value)} required />
        </label>
        <label className="inv-field">
          <span>{t("inventory.item.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="inv-field">
          <span>{t("inventory.item.uom")}</span>
          <input value={uom} onChange={(e) => setUom(e.target.value)} />
        </label>
        <label className="inv-field">
          <span>{t("inventory.item.type")}</span>
          <select value={type} onChange={(e) => setType(e.target.value as ItemType)}>
            <option value="stock">{t("inventory.types.stock")}</option>
            <option value="service">{t("inventory.types.service")}</option>
          </select>
        </label>
        <CustomFieldsForm
          defs={customFieldDefs ?? []}
          values={customValues}
          onChange={(k, v) => setCustomValues((prev) => ({ ...prev, [k]: v }))}
          errors={customErrors}
          fieldClassName="inv-field"
        />
        {recovery.conflict && <p className="muted" role="status">{t("drafts.conflict")}</p>}
        <DraftStatusIndicator status={recovery.status} savedAt={recovery.savedAt} />
        <button type="button" className="btn btn--sm btn--ghost" onClick={() => setShowForm(false)}>
          {t("common.cancel")}
        </button>
        <button className="btn btn--primary" type="submit">
          {t("inventory.item.add")}
        </button>
      </form>
      )}

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("inventory.item.empty")} hint={t("inventory.item.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="inv-filters listbar">
          <SavedViews api={savedViews} />
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && (
        <StatusTabs
          rows={filtered}
          tabs={typeTabs}
          accessor={(i) => i.type}
          value={tab}
          onChange={setTab}
          ariaLabel={t("inventory.item.type")}
        />
      )}
      {data && data.length > 0 && visible && visible.length === 0 && (
        <EmptyState
          title={t("filter.noMatch")}
          hint={t("filter.noMatchHint")}
          action={{ label: t("filter.clearAll"), onClick: () => setFilters([]) }}
        />
      )}

      {visible && visible.length > 0 && (
        <div className="card inv-table-wrap">
          <table className="inv-table">
            <thead>
              <tr>
                <SelectAllCell
                  className="inv-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("inventory.item.sku")}</th>
                <th>{t("inventory.item.name")}</th>
                <th>{t("inventory.item.uom")}</th>
                <th>{t("inventory.item.type")}</th>
                {(customFieldDefs ?? []).map((def) => (
                  <th key={def.key}>{isArabic ? def.label_ar : def.label_en}</th>
                ))}
                <th />
              </tr>
            </thead>
            <tbody>
              {visible.map((i, idx) => (
                <tr
                  key={i.id}
                  data-kbd-active={idx === active ? "true" : undefined}
                  data-selected={selection.isSelected(i.id) ? "true" : undefined}
                  aria-selected={selection.isSelected(i.id) || idx === active}
                >
                  <SelectRowCell
                    className="inv-table__select"
                    checked={selection.isSelected(i.id)}
                    onToggle={(shiftKey) => selection.toggle(idx, shiftKey)}
                  />
                  <td><EntityLink type="item" value={i.sku} /></td>
                  <td>{i.name}</td>
                  <td>{i.uom}</td>
                  <td>{t(`inventory.types.${i.type}`)}</td>
                  {(customFieldDefs ?? []).map((def) => (
                    <td key={def.key}>{formatCustomFieldValue(def, i.custom_data?.[def.key])}</td>
                  ))}
                  <td>
                    {i.type === "stock" && (
                      <RowActions label={t("common.actions")}>
                        <Link className="btn btn--sm" to={`/inventory?sku=${encodeURIComponent(i.sku)}`}>
                          {t("inventory.item.viewStock")}
                        </Link>
                      </RowActions>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BulkActionBar count={selection.count} onClear={selection.clear}>
        <button
          className="btn btn--sm"
          onClick={() => downloadCsv("items-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
