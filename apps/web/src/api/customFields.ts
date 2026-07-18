// Typed wrappers for the custom-field-definitions API (/api/core/custom-fields). Definitions are
// the source of truth for validation, table columns, and the dynamic form on customers/items;
// values live inline on the owning record's own `custom_data` field (see api/sales.ts, api/inventory.ts).
import { apiFetch } from "./client";

export type CustomFieldType = "TEXT" | "NUMBER" | "DATE" | "CHOICE" | "MONEY";
export type CustomFieldEntity = "sales.customer" | "inventory.item" | "purchasing.supplier";

export interface CustomFieldDef {
  id: number;
  entity_key: CustomFieldEntity;
  key: string;
  label_ar: string;
  label_en: string;
  type: CustomFieldType;
  required: boolean;
  choices: string[];
  is_active: boolean;
  position: number;
}

/** Active defs for an entity (any authenticated user — a form needs this to render). */
export function listCustomFieldDefs(entity: CustomFieldEntity): Promise<CustomFieldDef[]> {
  return apiFetch<CustomFieldDef[]>(`/core/custom-fields?entity=${encodeURIComponent(entity)}`);
}

export function createCustomFieldDef(payload: {
  entity_key: CustomFieldEntity;
  key: string;
  label_ar: string;
  label_en: string;
  type: CustomFieldType;
  required?: boolean;
  choices?: string[];
  position?: number;
}): Promise<CustomFieldDef> {
  return apiFetch<CustomFieldDef>("/core/custom-fields", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCustomFieldDef(
  id: number,
  patch: Partial<{
    label_ar: string;
    label_en: string;
    type: CustomFieldType;
    required: boolean;
    choices: string[];
    position: number;
  }>,
): Promise<CustomFieldDef> {
  return apiFetch<CustomFieldDef>(`/core/custom-fields/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deactivateCustomFieldDef(id: number): Promise<CustomFieldDef> {
  return apiFetch<CustomFieldDef>(`/core/custom-fields/${id}/deactivate`, { method: "POST" });
}
