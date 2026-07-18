// Shared logic for rendering + validating admin-defined custom fields (twenty-harvest FILE_12).
// Definitions are fetched once per entity; values live in a record's own `custom_data` map.
import type { CustomFieldDef } from "../api/customFields";
import { formatMinor } from "./money";

export type CustomFieldValues = Record<string, string>;

/** Client-side mirror of the backend's `validate_custom_data` (erp/core/custom_fields.py) — catches
 * the common mistakes (required, choice membership, number/money shape) before a round-trip, so the
 * form can point at the exact field instead of bouncing a generic server error. */
export function validateCustomFieldValues(
  defs: CustomFieldDef[],
  values: CustomFieldValues,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const def of defs) {
    const raw = (values[def.key] ?? "").trim();
    if (!raw) {
      if (def.required) errors[def.key] = `${def.label_en} / ${def.label_ar}`;
      continue;
    }
    if (def.type === "NUMBER" || def.type === "MONEY") {
      if (!/^-?\d+(\.\d+)?$/.test(raw)) errors[def.key] = `${def.label_en} / ${def.label_ar}`;
    } else if (def.type === "DATE") {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) errors[def.key] = `${def.label_en} / ${def.label_ar}`;
    } else if (def.type === "CHOICE") {
      if (!def.choices.includes(raw)) errors[def.key] = `${def.label_en} / ${def.label_ar}`;
    }
  }
  return errors;
}

/** `custom_data` values as the wire shape the create endpoints expect (money -> integer minor
 * units, blank optional fields dropped so an inactive/untouched key never gets written). */
export function buildCustomData(
  defs: CustomFieldDef[],
  values: CustomFieldValues,
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const def of defs) {
    const raw = (values[def.key] ?? "").trim();
    if (!raw) continue;
    out[def.key] = def.type === "MONEY" ? Math.round(parseFloat(raw) * 100) : raw;
  }
  return out;
}

/** A stored value formatted for read-only display (table cell / detail fact). */
export function formatCustomFieldValue(def: CustomFieldDef, raw: unknown): string {
  if (raw === null || raw === undefined || raw === "") return "";
  if (def.type === "MONEY") return formatMinor(Number(raw));
  return String(raw);
}
