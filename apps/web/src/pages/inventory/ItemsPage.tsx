import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { createItem, listItems, type Item, type ItemType } from "../../api/inventory";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { optimisticCreate } from "../../lib/optimistic";
import { matchesAllFilters, type ActiveFilter, type FilterField } from "../../lib/filters";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { FilterBar } from "../../components/FilterBar";
import { StatusTabs, ALL_TAB } from "../../components/StatusTabs";
import { InventoryNav } from "./InventoryNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./inventory.css";

const ITEM_TYPES: ItemType[] = ["stock", "service"];

export function ItemsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(listItems, [], "inventory:items");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
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

  const [sku, setSku] = useState("");
  const [name, setName] = useState("");
  const [uom, setUom] = useState("unit");
  const [type, setType] = useState<ItemType>("stock");

  // Optimistic create: show the new item row instantly and clear the form for the next entry; the
  // server row replaces the placeholder on settle, or it rolls back + toasts.
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const s = sku.trim();
    const n = name.trim();
    if (!s || !n) return;
    const u = uom.trim() || "unit";
    void optimisticCreate<Item>({
      current: data ?? [],
      mutate,
      placeholder: (id) => ({ id, sku: s, name: n, uom: u, type }) as Item,
      request: () => createItem({ sku: s, name: n, uom: u, type }),
      toast,
      success: t("inventory.toast.itemCreated"),
    });
    setSku("");
    setName("");
  }

  return (
    <section className="inv-page">
      <InventoryNav />

      <form className="card inv-toolbar" onSubmit={onSubmit}>
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
        <button className="btn btn--primary" type="submit">
          {t("inventory.item.add")}
        </button>
      </form>

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && data.length === 0 && (
        <EmptyState title={t("inventory.item.empty")} hint={t("inventory.item.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="inv-filters">
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
        <EmptyState title={t("filter.noMatch")} hint={t("filter.noMatchHint")} />
      )}

      {visible && visible.length > 0 && (
        <div className="card inv-table-wrap">
          <table className="inv-table">
            <thead>
              <tr>
                <th>{t("inventory.item.sku")}</th>
                <th>{t("inventory.item.name")}</th>
                <th>{t("inventory.item.uom")}</th>
                <th>{t("inventory.item.type")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((i) => (
                <tr key={i.id}>
                  <td><Bdi>{i.sku}</Bdi></td>
                  <td>{i.name}</td>
                  <td>{i.uom}</td>
                  <td>{t(`inventory.types.${i.type}`)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
