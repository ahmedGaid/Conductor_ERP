import { useTranslation } from "react-i18next";

interface Props {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export function ApprovalStepForm({ config, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <label className="field">
      <span>{t("automations.field.approverRole")}</span>
      <input
        value={(config.approver_role as string) ?? ""}
        onChange={(e) => onChange({ ...config, approver_role: e.target.value })}
      />
    </label>
  );
}
