import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { createSupplier, listSuppliers, type Supplier } from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { RowActions } from "../../components/RowActions";
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

  const [code, setCode] = useState("");
  const [name, setName] = useState("");

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

      <form className="card pur-toolbar" onSubmit={onSubmit}>
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
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id}>
                  <td><Bdi>{s.code}</Bdi></td>
                  <td>{s.name}</td>
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
    </section>
  );
}
