import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { createSupplier, listSuppliers, type Supplier } from "../../api/purchasing";
import { listCustomFieldDefs } from "../../api/customFields";
import { buildCustomData, formatCustomFieldValue, validateCustomFieldValues, type CustomFieldValues } from "../../lib/customFields";
import { CustomFieldsForm } from "../../components/CustomFieldsForm";
import { useAsync } from "../../hooks/useAsync";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { useFormKeys } from "../../hooks/useFormKeys";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { useActionFeedback } from "../../app/ActionFeedbackContext";
import { showSupplierReceipt } from "../../lib/feedback/purchasing";
import { optimisticCreate } from "../../lib/optimistic";
import { usePrefill } from "../../lib/usePrefill";
import { useListPageActions } from "../../hooks/useListPageActions";
import { downloadCsv, rowsToCsv, type CsvColumn } from "../../lib/csvExport";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { PartyLink } from "../../components/PartyLink";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { SavedViews } from "../../components/SavedViews";
import { useSavedViews } from "../../hooks/useSavedViews";
import { RowActions } from "../../components/RowActions";
import { ImportDialog } from "../../components/ImportDialog";
import type { ImportFieldInfo } from "../../api/imports";
import { PurchasingNav } from "./PurchasingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import { useSetHelpSignals } from "../../help/HelpSignalsContext";
import "./purchasing.css";

export function SuppliersPage() {
  const { t, i18n } = useTranslation();
  const isArabic = i18n.resolvedLanguage?.startsWith("ar") ?? true;
  const toast = useToast();
  const fb = useActionFeedback();
  const { data, loading, error, reload, mutate } = useAsync(listSuppliers, [], "purchasing:suppliers");
  const { data: customFieldDefs } = useAsync(
    () => listCustomFieldDefs("purchasing.supplier"),
    [],
    "settings:customFields:purchasing.supplier",
  );
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<Supplier>[]>(
    () => [
      { key: "code", label: t("purchasing.supplier.code"), type: "text", accessor: (s) => s.code },
      { key: "name", label: t("purchasing.supplier.name"), type: "text", accessor: (s) => s.name },
    ],
    [t],
  );
  const savedViews = useSavedViews({ listKey: "purchasing:suppliers", fields, filters, setFilters });
  const filtered = useMemo(
    () => (data ? data.filter((s) => matchesAllFilters(s, fields, filters)) : data),
    [data, fields, filters],
  );

  // j/k move a row highlight, Enter/o opens the supplier's party page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<Supplier>({
    items: filtered ?? [],
    onOpen: (s) => navigate(`/purchasing/suppliers/${encodeURIComponent(s.code)}`),
    persistKey: "purchasing:suppliers",
    getItemId: (s) => s.id,
  });

  // Multi-select for bulk CSV export — suppliers have no lifecycle verb, so this is the only bulk
  // action (still worth checkbox + Shift-range + ⌘A, per FILE_05: "any table" qualifies for export).
  const selection = useRowSelection<Supplier>({
    items: filtered ?? [],
    getItemId: (s) => s.id,
    activeIndex: active,
  });

  // Add is a form (forms keep their controls) — no bar primary, just print + CSV.
  const csvColumns = useMemo<CsvColumn<Supplier>[]>(
    () => [
      { header: t("purchasing.supplier.code"), accessor: (s) => s.code },
      { header: t("purchasing.supplier.name"), accessor: (s) => s.name },
    ],
    [t],
  );
  useListPageActions({ rows: filtered, columns: csvColumns, filename: "suppliers" });

  // Assistant deep links land here with the extracted values (?prefill=…) — additive only.
  const prefill = usePrefill(["code", "name"]);
  const [code, setCode] = useState(prefill.code ?? "");
  const [name, setName] = useState(prefill.name ?? "");
  const [importOpen, setImportOpen] = useState(false);
  const [customValues, setCustomValues] = useState<CustomFieldValues>({});
  const [customErrors, setCustomErrors] = useState<Record<string, string>>({});

  // ⌘/Ctrl+Enter submits the add form from any field.
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

  // Publish the page's live facts for the Help drawer's Live tab.
  useSetHelpSignals({
    codeSet: code.trim() !== "",
    nameSet: name.trim() !== "",
    supplierCount: (data ?? []).length,
  });

  const importFields = useMemo<ImportFieldInfo[]>(
    () => [
      { name: "code", label: t("purchasing.supplier.code"), required: true },
      { name: "name", label: t("purchasing.supplier.name"), required: true },
      { name: "is_active", label: t("purchasing.supplier.active") },
    ],
    [t],
  );

  // Optimistic create: show the new supplier row at once and clear the form so the next one can be
  // typed without waiting; the server row replaces the placeholder on settle, or it rolls back + toasts.
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const c = code.trim();
    const n = name.trim();
    if (!c || !n) return;
    const defs = customFieldDefs ?? [];
    const errors = validateCustomFieldValues(defs, customValues);
    if (Object.keys(errors).length > 0) {
      setCustomErrors(errors);
      return;
    }
    setCustomErrors({});
    const custom_data = buildCustomData(defs, customValues);
    void optimisticCreate<Supplier>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, code: c, name: n, custom_data }) as Supplier,
      request: () => createSupplier({ code: c, name: n, custom_data }),
      toast,
    }).then((created) => {
      if (created) showSupplierReceipt(fb, t, created, { navigate });
    });
    setCode("");
    setName("");
    setCustomValues({});
  }

  return (
    <section className="pur-page">
      <PurchasingNav />

      <div className="pur-page-actions">
        <button type="button" className="btn btn--sm" onClick={() => setImportOpen(true)}>
          {t("import.action")}
        </button>
      </div>

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        basePath="/purchasing/suppliers"
        title={t("import.suppliers.title")}
        templateName="suppliers-template.csv"
        fields={importFields}
        onCommitted={() => reload()}
      />

      <form ref={formRef} className="card pur-toolbar" onSubmit={onSubmit}>
        <label className="pur-field">
          <span>{t("purchasing.supplier.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="pur-field">
          <span>{t("purchasing.supplier.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <CustomFieldsForm
          defs={customFieldDefs ?? []}
          values={customValues}
          onChange={(k, v) => setCustomValues((prev) => ({ ...prev, [k]: v }))}
          errors={customErrors}
          fieldClassName="pur-field"
        />
        <button className="btn btn--primary" type="submit">
          {t("purchasing.supplier.add")}
        </button>
      </form>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("purchasing.supplier.empty")} hint={t("purchasing.supplier.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="pur-filters">
          <SavedViews api={savedViews} />
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
        <div className="card pur-table-wrap">
          <table className="pur-table">
            <thead>
              <tr>
                <SelectAllCell
                  className="pur-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("purchasing.supplier.code")}</th>
                <th>{t("purchasing.supplier.name")}</th>
                {(customFieldDefs ?? []).map((def) => (
                  <th key={def.key}>{isArabic ? def.label_ar : def.label_en}</th>
                ))}
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => (
                <tr
                  key={s.id}
                  data-kbd-active={i === active ? "true" : undefined}
                  data-selected={selection.isSelected(s.id) ? "true" : undefined}
                  aria-selected={selection.isSelected(s.id) || i === active}
                >
                  <SelectRowCell
                    className="pur-table__select"
                    checked={selection.isSelected(s.id)}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
                  <td>
                    <PartyLink type="supplier" code={s.code} className="latin">
                      <Bdi>{s.code}</Bdi>
                    </PartyLink>
                  </td>
                  <td>
                    <PartyLink type="supplier" code={s.code}>{s.name}</PartyLink>
                  </td>
                  {(customFieldDefs ?? []).map((def) => (
                    <td key={def.key}>{formatCustomFieldValue(def, s.custom_data?.[def.key])}</td>
                  ))}
                  <td>
                    <RowActions label={t("common.actions")}>
                      <Link className="btn btn--sm" to={`/purchasing?supplier=${encodeURIComponent(s.name)}`}>
                        {t("purchasing.supplier.viewOrders")}
                      </Link>
                    </RowActions>
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
          onClick={() => downloadCsv("suppliers-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
