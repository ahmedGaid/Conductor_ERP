import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createCustomer, listCustomers, type Customer } from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useFormKeys } from "../../hooks/useFormKeys";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { useActionFeedback } from "../../app/ActionFeedbackContext";
import { showCustomerReceipt } from "../../lib/feedback/sales";
import { optimisticCreate } from "../../lib/optimistic";
import { formatMinor, parseToMinor } from "../../lib/money";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { PartyLink } from "../../components/PartyLink";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { ImportDialog } from "../../components/ImportDialog";
import type { ImportFieldInfo } from "../../api/imports";
import { SalesNav } from "./SalesNav";
import { ListSkeleton } from "../../components/ListSkeleton";
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

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [limit, setLimit] = useState("");
  const [importOpen, setImportOpen] = useState(false);

  // ⌘/Ctrl+Enter submits the add form from any field (incl. the credit-limit input).
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

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
                <th>{t("sales.customer.code")}</th>
                <th>{t("sales.customer.name")}</th>
                <th className="sales-table__num">{t("sales.customer.creditLimit")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => (
                <tr key={c.id} data-kbd-active={i === active ? "true" : undefined} aria-selected={i === active}>
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
