import { useTranslation } from "react-i18next";

import type { CustomFieldDef } from "../api/customFields";
import type { CustomFieldValues } from "../lib/customFields";
import { ComboBox } from "./ComboBox";
import { DatePicker } from "./DatePicker";
import "./CustomFieldsForm.css";

interface CustomFieldsFormProps {
  defs: CustomFieldDef[];
  values: CustomFieldValues;
  onChange: (key: string, value: string) => void;
  errors?: Record<string, string>;
  /** Matches the surrounding form's field class (e.g. "inv-field", "sales-field", "admin-field"). */
  fieldClassName: string;
}

/** Renders one input per active custom-field def, matched to its type — reused by every create
 * form on an entity that carries custom fields (twenty-harvest FILE_12 Task B). */
export function CustomFieldsForm({ defs, values, onChange, errors, fieldClassName }: CustomFieldsFormProps) {
  const { i18n } = useTranslation();
  const isArabic = i18n.resolvedLanguage?.startsWith("ar") ?? true;

  if (defs.length === 0) return null;

  return (
    <>
      {defs.map((def) => {
        const label = isArabic ? def.label_ar : def.label_en;
        const value = values[def.key] ?? "";
        const error = errors?.[def.key];
        return (
          <label key={def.key} className={fieldClassName}>
            <span>
              {label}
              {def.required && <span aria-hidden="true"> *</span>}
            </span>
            {def.type === "DATE" ? (
              <DatePicker value={value} onChange={(v) => onChange(def.key, v)} />
            ) : def.type === "CHOICE" ? (
              <ComboBox
                value={value}
                onChange={(v) => onChange(def.key, v)}
                placeholder={label}
                options={def.choices.map((c) => ({ value: c, label: c }))}
              />
            ) : (
              <input
                className={def.type === "NUMBER" || def.type === "MONEY" ? "latin" : undefined}
                inputMode={def.type === "NUMBER" || def.type === "MONEY" ? "decimal" : undefined}
                value={value}
                onChange={(e) => onChange(def.key, e.target.value)}
              />
            )}
            {error && (
              <span className="custom-field-error" role="alert">
                {error}
              </span>
            )}
          </label>
        );
      })}
    </>
  );
}
