import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { createCustomer, listCustomers, type Customer } from "../../api/sales";
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
import { useActionFeedback } from "../../app/ActionFeedbackContext";
import { showCustomerReceipt } from "../../lib/feedback/sales";
import { optimisticCreate } from "../../lib/optimistic";
import { usePrefill } from "../../lib/usePrefill";
import { formatMinor, parseToMinor } from "../../lib/money";
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
import { SalesNav } from "./SalesNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import { useSetHelpSignals } from "../../help/HelpSignalsContext";
import "./sales.css";

// The shape autosaved as a draft. Kept as one object so the draft is a single value the hook can
// diff, while the fields stay in their own useState (the form reads/writes them field by field).
interface CustomerDraft {
  code: string;
  name: string;
  limit: string;
  taxReg: string;
  nationalId: string;
  custom: CustomFieldValues;
}

const EMPTY_CUSTOMER_DRAFT: CustomerDraft = {
  code: "", name: "", limit: "", taxReg: "", nationalId: "", custom: {},
};

export function CustomersPage() {
  const { t, i18n } = useTranslation();
  const isArabic = i18n.resolvedLanguage?.startsWith("ar") ?? true;
  const toast = useToast();
  const fb = useActionFeedback();
  const { data, loading, error, reload, mutate } = useAsync(listCustomers, [], "sales:customers");
  const { data: customFieldDefs } = useAsync(
    () => listCustomFieldDefs("sales.customer"),
    [],
    "settings:customFields:sales.customer",
  );
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<Customer>[]>(
    () => [
      { key: "code", label: t("sales.customer.code"), type: "text", accessor: (c) => c.code },
      { key: "name", label: t("sales.customer.name"), type: "text", accessor: (c) => c.name },
    ],
    [t],
  );
  const savedViews = useSavedViews({ listKey: "sales:customers", fields, filters, setFilters });
  const filtered = useMemo(
    () => (data ? data.filter((c) => matchesAllFilters(c, fields, filters)) : data),
    [data, fields, filters],
  );

  // j/k move a row highlight, Enter/o opens the customer's party page.
  const navigate = useNavigate();
  const { active } = useListKeyboardNav<Customer>({
    items: filtered ?? [],
    onOpen: (c) => navigate(`/sales/customers/${encodeURIComponent(c.code)}`),
    persistKey: "sales:customers",
    getItemId: (c) => c.id,
  });

  // Multi-select for bulk CSV export — customers have no lifecycle verb, so this is the only bulk
  // action (still worth checkbox + Shift-range + ⌘A, per FILE_05: "any table" qualifies for export).
  const selection = useRowSelection<Customer>({
    items: filtered ?? [],
    getItemId: (c) => c.id,
    activeIndex: active,
  });

  // Add is a multi-field form (forms keep their controls) — no bar primary, just print + CSV.
  const csvColumns = useMemo<CsvColumn<Customer>[]>(
    () => [
      { header: t("sales.customer.code"), accessor: (c) => c.code },
      { header: t("sales.customer.name"), accessor: (c) => c.name },
      {
        header: t("sales.customer.creditLimit"),
        accessor: (c) => (c.credit_limit_minor ? formatMinor(c.credit_limit_minor) : t("sales.customer.unlimited")),
      },
    ],
    [t],
  );
  useListPageActions({ rows: filtered, columns: csvColumns, filename: "customers" });

  // Assistant deep links land here with the extracted values (?prefill=…) — additive only.
  const prefill = usePrefill(["code", "name"]);
  const [code, setCode] = useState(prefill.code ?? "");
  const [name, setName] = useState(prefill.name ?? "");
  const [limit, setLimit] = useState("");
  const [taxReg, setTaxReg] = useState("");
  const [nationalId, setNationalId] = useState("");
  const [identityError, setIdentityError] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [customValues, setCustomValues] = useState<CustomFieldValues>({});
  const [customErrors, setCustomErrors] = useState<Record<string, string>>({});
  const [showForm, setShowForm] = useState(() => !!(prefill.code || prefill.name));

  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef, onCancel: () => setShowForm(false) });

  // Autosave the half-typed customer so closing the tab (or a crash) doesn't lose it.
  const draft = useMemo<CustomerDraft>(
    () => ({ code, name, limit, taxReg, nationalId, custom: customValues }),
    [code, name, limit, taxReg, nationalId, customValues],
  );
  const recovery = useDraftRecovery<CustomerDraft>({
    workflowKey: "sales.customer.create",
    entityType: "customer",
    value: draft,
    baseline: EMPTY_CUSTOMER_DRAFT,
    schemaVersion: 1,
  });

  function applyDraft(d: CustomerDraft) {
    setCode(d.code ?? "");
    setName(d.name ?? "");
    setLimit(d.limit ?? "");
    setTaxReg(d.taxReg ?? "");
    setNationalId(d.nationalId ?? "");
    setCustomValues(d.custom ?? {});
    setShowForm(true);
  }

  // Publish the page's live facts for the Help drawer's Live tab.
  useSetHelpSignals({
    codeSet: code.trim() !== "",
    nameSet: name.trim() !== "",
    customerCount: (data ?? []).length,
  });

  const importFields = useMemo<ImportFieldInfo[]>(
    () => [
      { name: "code", label: t("sales.customer.code"), required: true },
      { name: "name", label: t("sales.customer.name"), required: true },
      { name: "credit_limit", label: t("sales.customer.creditLimit") },
      { name: "is_active", label: t("sales.customer.active") },
    ],
    [t],
  );

  // Optimistic create: show the new customer instantly and clear the form for the next entry; the
  // server row replaces the placeholder on settle, or it rolls back + toasts.
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const c = code.trim();
    const n = name.trim();
    if (!c || !n) return;
    const taxRegistration = taxReg.trim();
    const national = nationalId.trim();
    // National ID is the fallback identity when there is no tax registration number; validate its
    // shape (Egyptian national ID is 14 digits) before sending.
    if (national && !/^\d{14}$/.test(national)) {
      setIdentityError(t("sales.customer.nationalIdInvalid"));
      return;
    }
    if (taxRegistration && !/^\d+$/.test(taxRegistration)) {
      setIdentityError(t("sales.customer.taxRegInvalid"));
      return;
    }
    setIdentityError("");
    const defs = customFieldDefs ?? [];
    const errors = validateCustomFieldValues(defs, customValues);
    if (Object.keys(errors).length > 0) {
      setCustomErrors(errors);
      return;
    }
    setCustomErrors({});
    const credit = parseToMinor(limit) ?? 0;
    const custom_data = buildCustomData(defs, customValues);
    void optimisticCreate<Customer>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({
        id, code: c, name: n, credit_limit_minor: credit,
        tax_registration_number: taxRegistration, national_id: national, custom_data,
      }) as Customer,
      request: () => createCustomer({
        code: c, name: n, credit_limit_minor: credit,
        tax_registration_number: taxRegistration, national_id: national, custom_data,
      }),
      toast,
    }).then((created) => {
      if (created) showCustomerReceipt(fb, t, created, { navigate });
      // The workflow finished — the draft must not come back on the next visit.
      void recovery.complete(created ? String(created.id) : undefined);
    });
    setCode("");
    setName("");
    setLimit("");
    setTaxReg("");
    setNationalId("");
    setCustomValues({});
    setShowForm(false);
  }

  return (
    <section className="sales-page">
      <SalesNav />

      <div className="sales-page-actions">
        <button type="button" className="btn btn--sm" onClick={() => setImportOpen(true)}>
          {t("import.action")}
        </button>
        {!showForm && (
          <button type="button" className="btn btn--sm btn--primary" onClick={() => setShowForm(true)}>
            {t("sales.customer.add")}
          </button>
        )}
      </div>

      {recovery.recoverable && (
        <DraftRecoveryBanner
          entityLabel={t("drafts.workflow.sales.customer.create")}
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
        basePath="/sales/customers"
        title={t("import.customers.title")}
        templateName="customers-template.csv"
        fields={importFields}
        onCommitted={() => reload()}
      />

      {showForm && (
      <form ref={formRef} className="card sales-toolbar" onSubmit={onSubmit}>
        <label className="sales-field">
          <span>{t("sales.customer.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="sales-field">
          <span>{t("sales.customer.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="sales-field">
          <span>{t("sales.customer.creditLimit")}</span>
          <input className="latin" inputMode="decimal" value={limit} onChange={(e) => setLimit(e.target.value)} placeholder="0.00" />
        </label>
        <label className="sales-field">
          <span>{t("sales.customer.taxRegistrationNumber")}</span>
          <input className="latin" inputMode="numeric" value={taxReg} onChange={(e) => setTaxReg(e.target.value)} placeholder={t("sales.customer.optional")} />
        </label>
        <label className="sales-field">
          <span>{t("sales.customer.nationalId")}</span>
          <input className="latin" inputMode="numeric" value={nationalId} onChange={(e) => setNationalId(e.target.value)} placeholder={t("sales.customer.nationalIdHint")} />
        </label>
        {identityError && <p className="custom-field-error" role="alert">{identityError}</p>}
        <CustomFieldsForm
          defs={customFieldDefs ?? []}
          values={customValues}
          onChange={(k, v) => setCustomValues((prev) => ({ ...prev, [k]: v }))}
          errors={customErrors}
          fieldClassName="sales-field"
        />
        {recovery.conflict && <p className="muted" role="status">{t("drafts.conflict")}</p>}
        <DraftStatusIndicator status={recovery.status} savedAt={recovery.savedAt} />
        <button type="button" className="btn btn--sm btn--ghost" onClick={() => setShowForm(false)}>
          {t("common.cancel")}
        </button>
        <button className="btn btn--primary" type="submit">
          {t("sales.customer.add")}
        </button>
      </form>
      )}

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("sales.customer.empty")} hint={t("sales.customer.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="sales-filters">
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
        <div className="card sales-table-wrap">
          <table className="sales-table">
            <thead>
              <tr>
                <SelectAllCell
                  className="sales-table__select"
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggleAll={selection.toggleAll}
                />
                <th>{t("sales.customer.code")}</th>
                <th>{t("sales.customer.name")}</th>
                <th className="sales-table__num">{t("sales.customer.creditLimit")}</th>
                {(customFieldDefs ?? []).map((def) => (
                  <th key={def.key}>{isArabic ? def.label_ar : def.label_en}</th>
                ))}
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => (
                <tr
                  key={c.id}
                  data-kbd-active={i === active ? "true" : undefined}
                  data-selected={selection.isSelected(c.id) ? "true" : undefined}
                  aria-selected={selection.isSelected(c.id) || i === active}
                >
                  <SelectRowCell
                    className="sales-table__select"
                    checked={selection.isSelected(c.id)}
                    onToggle={(shiftKey) => selection.toggle(i, shiftKey)}
                  />
                  <td>
                    <PartyLink type="customer" code={c.code} className="latin">
                      <Bdi>{c.code}</Bdi>
                    </PartyLink>
                  </td>
                  <td>
                    <PartyLink type="customer" code={c.code}>{c.name}</PartyLink>
                  </td>
                  <td className="sales-table__num">
                    <Bdi>{c.credit_limit_minor ? formatMinor(c.credit_limit_minor) : t("sales.customer.unlimited")}</Bdi>
                  </td>
                  {(customFieldDefs ?? []).map((def) => (
                    <td key={def.key}>{formatCustomFieldValue(def, c.custom_data?.[def.key])}</td>
                  ))}
                  <td>
                    <RowActions label={t("common.actions")}>
                      <Link className="btn btn--sm" to={`/sales?customer=${encodeURIComponent(c.name)}`}>
                        {t("sales.customer.viewOrders")}
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
          onClick={() => downloadCsv("customers-selected", rowsToCsv(selection.selectedItems, csvColumns))}
        >
          {t("bulk.exportCsv")}
        </button>
      </BulkActionBar>
    </section>
  );
}
