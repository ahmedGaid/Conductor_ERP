import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createSupplier, listSuppliers, type Supplier } from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { useListKeyboardNav } from "../../hooks/useListKeyboardNav";
import { useFormKeys } from "../../hooks/useFormKeys";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { PartyLink } from "../../components/PartyLink";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { ImportDialog } from "../../components/ImportDialog";
import type { ImportFieldInfo } from "../../api/imports";
import { PurchasingNav } from "./PurchasingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./purchasing.css";

export function SuppliersPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(listSuppliers, [], "purchasing:suppliers");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<Supplier>[]>(
    () => [
      { key: "code", label: t("purchasing.supplier.code"), type: "text", accessor: (s) => s.code },
      { key: "name", label: t("purchasing.supplier.name"), type: "text", accessor: (s) => s.name },
    ],
    [t],
  );
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

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [importOpen, setImportOpen] = useState(false);

  // ⌘/Ctrl+Enter submits the add form from any field.
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

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
    void optimisticCreate<Supplier>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, code: c, name: n }) as Supplier,
      request: () => createSupplier({ code: c, name: n }),
      toast,
      success: t("purchasing.toast.supplierCreated"),
    });
    setCode("");
    setName("");
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
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {filtered && filtered.length > 0 && (
        <div className="card pur-table-wrap">
          <table className="pur-table">
            <thead>
              <tr>
                <th>{t("purchasing.supplier.code")}</th>
                <th>{t("purchasing.supplier.name")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => (
                <tr key={s.id} data-kbd-active={i === active ? "true" : undefined} aria-selected={i === active}>
                  <td>
                    <PartyLink type="supplier" code={s.code} className="latin">
                      <Bdi>{s.code}</Bdi>
                    </PartyLink>
                  </td>
                  <td>
                    <PartyLink type="supplier" code={s.code}>{s.name}</PartyLink>
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
