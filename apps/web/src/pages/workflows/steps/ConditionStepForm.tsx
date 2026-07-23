import { useTranslation } from "react-i18next";

import { ComboBox } from "../../../components/ComboBox";

interface Props {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

const OPERATORS = [">", "<", "=="] as const;

// Fixed vocabulary of context fields a condition can check — matches what the templates and the
// canvas's own condition node expose. A free-text field name can't be validated against the
// running context, so this list is the only thing that avoids a silently-dead condition.
const FIELDS = ["amount_minor", "days_overdue", "quantity", "days_since_created"] as const;

export function ConditionStepForm({ config, onChange }: Props) {
  const { t } = useTranslation();
  const fieldOptions = FIELDS.map((f) => ({ value: f, label: t(`automations.conditionField.${f}`) }));
  const operatorOptions = OPERATORS.map((op) => ({ value: op, label: t(`automations.conditionOperator.${op}`) }));

  return (
    <div className="steplist__condition">
      <label className="field">
        <span>{t("automations.steps.if")}</span>
        <ComboBox
          options={fieldOptions}
          value={(config.field as string) ?? ""}
          onChange={(v) => onChange({ ...config, field: v })}
          placeholder={t("automations.conditionFieldPlaceholder")}
        />
      </label>
      <ComboBox
        options={operatorOptions}
        value={(config.operator as string) ?? ""}
        onChange={(v) => onChange({ ...config, operator: v })}
        placeholder={t("automations.conditionOperatorPlaceholder")}
        aria-label={t("automations.field.operator")}
      />
      <label className="field">
        <span>{t("automations.field.value")}</span>
        <input
          type="number"
          inputMode="decimal"
          value={(config.value as number | undefined) ?? ""}
          onChange={(e) => onChange({ ...config, value: Number(e.target.value) })}
        />
      </label>
    </div>
  );
}
