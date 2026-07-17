import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { createCustomer, listCustomers, type Customer } from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useRowSelection } from "../../hooks/useRowSelection";
import { SelectAllCell, SelectRowCell } from "../../components/SelectionCell";
import { BulkActionBar } from "../../components/BulkActionBar";
import { useFormKeys } from "../../hooks/useFormKeys";
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
import { RowActions } from "../../components/RowActions";
import { ImportDialog } from "../../components/ImportDialog";
import type { ImportFieldInfo } from "../../api/imports";
import { SalesNav } from "./SalesNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import { useSetHelpSignals } from "../../help/HelpSignalsContext";
import "./sales.css";

export function CustomersPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const fb = useActionFeedback();
  const { data, loading, error, reload, mutate } = useAsync(listCustomers, [], "sales:customers");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<Customer>[]>(
    () => [
      { key: "code", label: t("sales.customer.code"), type: "text", accessor: (c) => c.code },
      { key: "name", label: t("sales.customer.name"), type: "text", accessor: (c) => c.name },
    ],
    [t],
  );
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
  const [importOpen, setImportOpen] = useState(false);

  // ⌘/Ctrl+Enter submits the add form from any field (incl. the credit-limit input).
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

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
    const credit = parseToMinor(limit) ?? 0;
    void optimisticCreate<Customer>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, code: c, name: n, credit_limit_minor: credit }) as Customer,
      request: () => createCustomer({ code: c, name: n, credit_limit_minor: credit }),
      toast,
    }).then((created) => {
      if (created) showCustomerReceipt(fb, t, created, { navigate });
    });
    setCode("");
    setName("");
    setLimit("");
  }

  return (
    <section className="sales-page">
      <SalesNav />

      <div className="sales-page-actions">
        <button type="button" className="btn btn--sm" onClick={() => setImportOpen(true)}>
          {t("import.action")}
        </button>
      </div>

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        basePath="/sales/customers"
        title={t("import.customers.title")}
        templateName="customers-template.csv"
        fields={importFields}
        onCommitted={() => reload()}
      />

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
        <button className="btn btn--primary" type="submit">
          {t("sales.customer.add")}
        </button>
      </form>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("sales.customer.empty")} hint={t("sales.customer.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="sales-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
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
