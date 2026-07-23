import { useTranslation } from "react-i18next";

interface Props {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export function NotificationStepForm({ config, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <label className="field">
      <span>{t("automations.field.recipient")}</span>
      <input
        value={(config.recipient as string) ?? ""}
        onChange={(e) => onChange({ ...config, recipient: e.target.value })}
      />
    </label>
  );
}
