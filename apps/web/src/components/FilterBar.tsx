import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  defaultOperator,
  newFilterId,
  operatorsFor,
  reconcileOperator,
  type ActiveFilter,
  type FilterField,
} from "../lib/filters";
import { Popover } from "./Popover";
import { Tooltip } from "./Tooltip";
import { NavIcon } from "../app/icons";
import "./FilterBar.css";

interface FilterBarProps<T> {
  fields: FilterField<T>[];
  filters: ActiveFilter[];
  onChange: (filters: ActiveFilter[]) => void;
}

/**
 * The filter editor: active filters render as chips ([field · operator · value · ✕]); a quiet
 * "Filter" button adds more. Each chip's operator adapts to the field type and value count. Holds
 * no data itself — the page owns the `filters` array and applies `matchesAllFilters` to its rows —
 * so the same bar drops onto any list. Built on the shared Popover + Tooltip; tokens-only styling.
 */
export function FilterBar<T>({ fields, filters, onChange }: FilterBarProps<T>) {
  const { t } = useTranslation();
  const [addOpen, setAddOpen] = useState(false);
  const [autoOpenId, setAutoOpenId] = useState<string | null>(null);
  const addRef = useRef<HTMLButtonElement | null>(null);

  function addFilter(field: FilterField<T>) {
    const id = newFilterId();
    onChange([...filters, { id, key: field.key, operator: defaultOperator(field as FilterField<unknown>), values: [] }]);
    setAddOpen(false);
    setAutoOpenId(id); // open its value editor straight away (Linear-style)
  }

  function updateFilter(next: ActiveFilter) {
    onChange(filters.map((f) => (f.id === next.id ? next : f)));
  }

  function removeFilter(id: string) {
    onChange(filters.filter((f) => f.id !== id));
  }

  return (
    <div className="filterbar">
      {filters.map((filter) => {
        const field = fields.find((f) => f.key === filter.key);
        if (!field) return null;
        return (
          <FilterChip
            key={filter.id}
            field={field}
            filter={filter}
            autoOpen={autoOpenId === filter.id}
            onChange={updateFilter}
            onRemove={() => removeFilter(filter.id)}
          />
        );
      })}

      <button
        ref={addRef}
        type="button"
        className="btn btn--ghost btn--sm filterbar__add"
        aria-haspopup="dialog"
        aria-expanded={addOpen}
        onClick={() => setAddOpen((o) => !o)}
      >
        <FunnelIcon />
        {t("filter.add")}
      </button>

      {filters.length > 0 && (
        <button type="button" className="btn btn--ghost btn--sm filterbar__clear" onClick={() => onChange([])}>
          {t("filter.clear")}
        </button>
      )}

      <Popover
        open={addOpen}
        onClose={() => setAddOpen(false)}
        anchorRef={addRef}
        ariaLabel={t("filter.add")}
      >
        <div className="popover__menu">
          {fields.map((field) => (
            <button
              key={field.key}
              type="button"
              className="popover__item"
              onClick={() => addFilter(field)}
            >
              {field.label}
            </button>
          ))}
        </div>
      </Popover>
    </div>
  );
}

function FilterChip<T>({
  field,
  filter,
  autoOpen,
  onChange,
  onRemove,
}: {
  field: FilterField<T>;
  filter: ActiveFilter;
  autoOpen: boolean;
  onChange: (next: ActiveFilter) => void;
  onRemove: () => void;
}) {
  const { t } = useTranslation();
  const [opOpen, setOpOpen] = useState(false);
  const [valOpen, setValOpen] = useState(autoOpen);
  const [search, setSearch] = useState("");
  const opRef = useRef<HTMLButtonElement | null>(null);
  const valRef = useRef<HTMLButtonElement | null>(null);

  const operators = operatorsFor(field as FilterField<unknown>, filter.values);

  function setOperator(op: ActiveFilter["operator"]) {
    onChange({ ...filter, operator: op });
    setOpOpen(false);
  }

  function setValues(values: string[]) {
    onChange({
      ...filter,
      values,
      operator: reconcileOperator(field as FilterField<unknown>, filter.operator, values),
    });
  }

  function toggleOption(value: string) {
    const has = filter.values.includes(value);
    setValues(has ? filter.values.filter((v) => v !== value) : [...filter.values, value]);
  }

  const valueSummary = summarize(field, filter, t);
  const options = (field.options ?? []).filter((o) =>
    o.label.toLowerCase().includes(search.trim().toLowerCase()),
  );

  return (
    <div className="filter-chip">
      <span className="filter-chip__field">{field.label}</span>

      <button
        ref={opRef}
        type="button"
        className="filter-chip__op"
        aria-haspopup="dialog"
        aria-expanded={opOpen}
        onClick={() => setOpOpen((o) => !o)}
      >
        {t(`filter.op.${filter.operator}`)}
      </button>

      <button
        ref={valRef}
        type="button"
        className="filter-chip__value"
        aria-haspopup="dialog"
        aria-expanded={valOpen}
        onClick={() => setValOpen((o) => !o)}
      >
        {valueSummary}
      </button>

      <Tooltip label={t("filter.remove")} placement="top">
        <button type="button" className="filter-chip__remove" aria-label={t("filter.remove")} onClick={onRemove}>
          <NavIcon name="close" />
        </button>
      </Tooltip>

      {/* Operator menu */}
      <Popover open={opOpen} onClose={() => setOpOpen(false)} anchorRef={opRef} ariaLabel={field.label}>
        <div className="popover__menu">
          {operators.map((op) => (
            <button
              key={op}
              type="button"
              className={op === filter.operator ? "popover__item popover__item--on" : "popover__item"}
              onClick={() => setOperator(op)}
            >
              {t(`filter.op.${op}`)}
              {op === filter.operator && <span className="popover__check" aria-hidden="true"><NavIcon name="check" /></span>}
            </button>
          ))}
        </div>
      </Popover>

      {/* Value editor */}
      <Popover open={valOpen} onClose={() => setValOpen(false)} anchorRef={valRef} ariaLabel={field.label}>
        {field.type === "select" && (
          <div className="popover__menu">
            <input
              type="text"
              className="popover__search"
              placeholder={t("filter.search")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label={t("filter.search")}
            />
            {options.length === 0 && <p className="popover__empty">{t("filter.noResults")}</p>}
            {options.map((o) => {
              const on = filter.values.includes(o.value);
              return (
                <button
                  key={o.value}
                  type="button"
                  className={on ? "popover__item popover__item--on" : "popover__item"}
                  aria-pressed={on}
                  onClick={() => toggleOption(o.value)}
                >
                  {o.label}
                  {on && <span className="popover__check" aria-hidden="true"><NavIcon name="check" /></span>}
                </button>
              );
            })}
          </div>
        )}

        {field.type === "text" && (
          <div className="popover__editor">
            <input
              type="text"
              autoFocus
              placeholder={field.label}
              value={filter.values[0] ?? ""}
              onChange={(e) => setValues(e.target.value ? [e.target.value] : [])}
              aria-label={field.label}
            />
          </div>
        )}

        {field.type === "date" && (
          <div className="popover__editor">
            <input
              type="date"
              className="latin"
              autoFocus
              value={filter.values[0] ?? ""}
              onChange={(e) => setValues(e.target.value ? [e.target.value] : [])}
              aria-label={field.label}
            />
          </div>
        )}
      </Popover>
    </div>
  );
}

function summarize<T>(
  field: FilterField<T>,
  filter: ActiveFilter,
  t: (key: string, opts?: Record<string, unknown>) => string,
): string {
  if (filter.values.length === 0) return t("filter.any");
  if (field.type === "select") {
    if (filter.values.length === 1) {
      return field.options?.find((o) => o.value === filter.values[0])?.label ?? filter.values[0];
    }
    return t("filter.nSelected", { count: filter.values.length });
  }
  return filter.values[0];
}

function FunnelIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M3 5h18l-7 8v5l-4 2v-7L3 5Z" />
    </svg>
  );
}
