/*
 * Composable list filtering — the data model + pure matching logic behind <FilterBar>.
 *
 * A page declares its filterable `FilterField`s (a key, a human label, a type, an accessor, and —
 * for "select" — the allowed options). The user builds `ActiveFilter`s as chips; the operator on
 * each chip ADAPTS to the field type and how many values are chosen (one value → "is"; several →
 * "is any of"), exactly like Linear. Matching runs client-side over the already-loaded rows, so it
 * benefits from the existing stale-while-revalidate cache with no extra requests.
 *
 * Operators are referenced by key only; the visible words live in i18n (`filter.op.*`, ar/en parity).
 */

export type FilterFieldType = "select" | "text" | "date";

export type FilterOperator =
  | "is"
  | "isNot"
  | "isAnyOf"
  | "isNoneOf"
  | "contains"
  | "notContains"
  | "before"
  | "after"
  | "on";

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterField<T> {
  /** Stable identifier, unique within a page's field set. */
  key: string;
  /** Already-translated, human label shown on the chip and in the add-filter menu. */
  label: string;
  type: FilterFieldType;
  /** Allowed choices for a "select" field (already translated). */
  options?: FilterOption[];
  /** Pulls the comparable value out of a row. */
  accessor: (row: T) => unknown;
}

export interface ActiveFilter {
  /** Instance id (a chip can repeat a field). */
  id: string;
  /** The FilterField.key this chip filters on. */
  key: string;
  operator: FilterOperator;
  /** Selected option values, the search text, or the chosen date — always as strings. */
  values: string[];
}

let counter = 0;
export function newFilterId(): string {
  counter += 1;
  return `f${counter}_${Date.now().toString(36)}`;
}

/** The operators offered for a field, given how many values are currently chosen (Linear-style). */
export function operatorsFor(field: FilterField<unknown>, values: string[]): FilterOperator[] {
  switch (field.type) {
    case "select":
      return values.length > 1 ? ["isAnyOf", "isNoneOf"] : ["is", "isNot"];
    case "text":
      return ["contains", "notContains"];
    case "date":
      return ["on", "before", "after"];
  }
}

/** The operator a new chip starts with. */
export function defaultOperator(field: FilterField<unknown>): FilterOperator {
  switch (field.type) {
    case "select":
      return "is";
    case "text":
      return "contains";
    case "date":
      return "on";
  }
}

/**
 * Keep the operator valid as the value count changes: a "select" chip flips between the single-value
 * operators (is / is not) and the multi-value ones (is any of / is none of) so it never shows a
 * mismatched verb. The polarity (positive vs. negative) is preserved.
 */
export function reconcileOperator(field: FilterField<unknown>, op: FilterOperator, values: string[]): FilterOperator {
  if (field.type !== "select") return op;
  const negative = op === "isNot" || op === "isNoneOf";
  if (values.length > 1) return negative ? "isNoneOf" : "isAnyOf";
  return negative ? "isNot" : "is";
}

function matchesOne<T>(row: T, field: FilterField<T>, filter: ActiveFilter): boolean {
  const raw = field.accessor(row);

  switch (field.type) {
    case "select": {
      const member = filter.values.includes(String(raw ?? ""));
      return filter.operator === "isNot" || filter.operator === "isNoneOf" ? !member : member;
    }
    case "text": {
      const needle = (filter.values[0] ?? "").trim().toLowerCase();
      if (!needle) return true;
      const hay = String(raw ?? "").toLowerCase();
      const has = hay.includes(needle);
      return filter.operator === "notContains" ? !has : has;
    }
    case "date": {
      const pick = filter.values[0] ?? "";
      if (!pick) return true;
      const value = String(raw ?? ""); // ISO yyyy-mm-dd sorts lexicographically
      if (filter.operator === "before") return value < pick;
      if (filter.operator === "after") return value > pick;
      return value === pick; // "on"
    }
  }
}

/** True when a row satisfies every active filter that actually carries a value. */
export function matchesAllFilters<T>(row: T, fields: FilterField<T>[], filters: ActiveFilter[]): boolean {
  for (const filter of filters) {
    if (filter.values.length === 0) continue; // an empty chip constrains nothing
    const field = fields.find((f) => f.key === filter.key);
    if (!field) continue;
    if (!matchesOne(row, field, filter)) return false;
  }
  return true;
}
