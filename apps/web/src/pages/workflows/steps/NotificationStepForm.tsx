import { useTranslation } from "react-i18next";

import { useAsync } from "../../../hooks/useAsync";
import { ComboBox } from "../../../components/ComboBox";
import { listUsers } from "../../../api/users";

interface Props {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export function NotificationStepForm({ config, onChange }: Props) {
  const { t } = useTranslation();
  const { data: users } = useAsync(() => listUsers(), []);
  const options = (users ?? []).map((u) => ({ value: u.username, label: u.display_name || u.username }));

  return (
    <label className="field">
      <span>{t("automations.field.recipient")}</span>
      <ComboBox
        options={options}
        value={(config.recipient as string) ?? ""}
        onChange={(v) => onChange({ ...config, recipient: v })}
        placeholder={t("automations.field.recipientPlaceholder")}
      />
    </label>
  );
}
