import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { listBatches } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { InventoryNav } from "./InventoryNav";
import "./inventory.css";

type Batch = Awaited<ReturnType<typeof listBatches>>[number];

export function BatchesPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(listBatches, [], "inventory:batches");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);

  const fields = useMemo<FilterField<Batch>[]>(
    () => [
      { key: "batch", label: t("inventory.batches.batch"), type: "text", accessor: (b) => b.batch_no },
      { key: "item", label: t("inventory.batches.item"), type: "text", accessor: (b) => `${b.sku} ${b.item_name}` },
      { key: "warehouse", label: t("inventory.batches.warehouse"), type: "text", accessor: (b) => b.warehouse_code },
    ],
    [t],
  );
  const filtered = useMemo(
    () => (data ? data.filter((b) => matchesAllFilters(b, fields, filters)) : data),
    [data, fields, filters],
  );

  return (
    <section className="inv-page">
      <InventoryNav />

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("inventory.batches.empty")} hint={t("inventory.batches.hint")} />
      )}

      {data && data.length > 0 && (
        <div className="inv-filters">
          <FilterBar fields={fields} filters={filters} onChange={setFilters} />
        </div>
      )}
      {data && data.length > 0 && filtered && filtered.length === 0 && (
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {filtered && filtered.length > 0 && (
        <div className="card inv-table-wrap">
          <table className="inv-table">
            <thead>
              <tr>
                <th>{t("inventory.batches.batch")}</th>
                <th>{t("inventory.batches.item")}</th>
                <th>{t("inventory.batches.warehouse")}</th>
                <th className="inv-table__num">{t("inventory.batches.received")}</th>
                <th>{t("inventory.batches.expiry")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((b, i) => (
                <tr key={`${b.batch_no}-${b.sku}-${b.warehouse_code}-${i}`}>
                  <td><Bdi>{b.batch_no}</Bdi></td>
                  <td><Bdi>{b.sku}</Bdi> · {b.item_name}</td>
                  <td><Bdi>{b.warehouse_code}</Bdi></td>
                  <td className="inv-table__num"><Bdi>{b.received_quantity}</Bdi></td>
                  <td>{b.earliest_expiry ? <Bdi>{b.earliest_expiry}</Bdi> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
