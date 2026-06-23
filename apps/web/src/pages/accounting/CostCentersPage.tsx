import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createCostCenter, listCostCenters } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./accounting.css";

type CostCenter = Awaited<ReturnType<typeof listCostCenters>>[number];

export function CostCentersPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(listCostCenters, [], "accounting:cost-centers");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<CostCenter>[]>(
    () => [
      { key: "code", label: t("accounting.costCenters.code"), type: "text", accessor: (cc) => cc.code },
      { key: "name", label: t("accounting.costCenters.name"), type: "text", accessor: (cc) => cc.name },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((cc) => matchesAllFilters(cc, fields, filters)) : data),
    [data, fields, filters],
  );

  const [code, setCode] = useState("");
  const [name, setName] = useState("");

  // Optimistic create: show the new cost center instantly and clear the form for the next entry; the
  // server row replaces the placeholder on settle, or it rolls back + toasts.
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const c = code.trim();
    const n = name.trim();
    if (!c || !n) return;
    void optimisticCreate<CostCenter>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, code: c, name: n, is_active: true }) as CostCenter,
      request: () => createCostCenter({ code: c, name: n }),
      toast,
      success: t("accounting.toast.costCenterCreated"),
    });
    setCode("");
    setName("");
  }

  return (
    <section className="acct-page">
      <AccountingNav />

      <form className="card acct-toolbar" onSubmit={onSubmit}>
        <label className="acct-field">
          <span>{t("accounting.costCenters.code")}</span>
          <input className="latin" value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label className="acct-field" style={{ flex: 1 }}>
          <span>{t("accounting.costCenters.name")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <button className="btn btn--primary" type="submit">
          {t("accounting.costCenters.add")}
        </button>
      </form>

      {loading && (
        <ListSkeleton rows={2} />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("accounting.costCenters.empty")} hint={t("common.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="acct-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {filtered && filtered.length > 0 && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.costCenters.code")}</th>
                <th>{t("accounting.costCenters.name")}</th>
                <th>{t("accounting.costCenters.active")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((cc) => (
                <tr key={cc.id}>
                  <td><Bdi>{cc.code}</Bdi></td>
                  <td>{cc.name}</td>
                  <td>{cc.is_active ? t("common.yes") : t("common.no")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
