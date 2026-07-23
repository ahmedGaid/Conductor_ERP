import { useTranslation } from "react-i18next";

interface Props {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

const OPERATORS = [">", "<", "=="] as const;

export function ConditionStepForm({ config, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <div className="steplist__condition">
      <label className="field">
        <span>{t("automations.field.amount")}</span>
        <input
          value={(config.field as string) ?? ""}
          onChange={(e) => onChange({ ...config, field: e.target.value })}
        />
      </label>
      <select
        value={(config.operator as string) ?? ">"}
        onChange={(e) => onChange({ ...config, operator: e.target.value })}
      >
        {OPERATORS.map((op) => (
          <option key={op} value={op}>
            {op}
          </option>
        ))}
      </select>
      <input
        value={(config.value as number | undefined) ?? ""}
        onChange={(e) => onChange({ ...config, value: Number(e.target.value) })}
      />
    </div>
  );
}
