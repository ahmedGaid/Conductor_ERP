import { useTranslation } from "react-i18next";

import { useAsync } from "../../../hooks/useAsync";
import { ComboBox } from "../../../components/ComboBox";
import { listRoles } from "../../../api/roles";

interface Props {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export function ApprovalStepForm({ config, onChange }: Props) {
  const { t } = useTranslation();
  const { data: roles } = useAsync(() => listRoles(), []);
  const options = (roles ?? []).map((r) => ({ value: r.name, label: r.name }));

  return (
    <label className="field">
      <span>{t("automations.field.approverRole")}</span>
      <ComboBox
        options={options}
        value={(config.approver_role as string) ?? ""}
        onChange={(v) => onChange({ ...config, approver_role: v })}
        placeholder={t("automations.field.approverRolePlaceholder")}
      />
    </label>
  );
}
