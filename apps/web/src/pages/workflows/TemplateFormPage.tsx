import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { ComboBox } from "../../components/ComboBox";
import { listTemplates, createFromTemplate, type WorkflowTemplate } from "../../api/workflowTemplates";
import { listRoles } from "../../api/roles";
import { listUsers } from "../../api/users";
import { formatMinor, parseToMinor } from "../../lib/money";
import "./AutomationsPage.css";

export function TemplateFormPage() {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { templateId } = useParams<{ templateId: string }>();
  const { data: templates, loading } = useAsync<WorkflowTemplate[]>(() => listTemplates(), []);
  const { data: roles } = useAsync(() => listRoles(), []);
  const { data: users } = useAsync(() => listUsers(), []);
  const template = templates?.find((tpl) => tpl.id === templateId);
  const lang = i18n.language as "ar" | "en";
  const [name, setName] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  if (loading || !template) return null;

  const roleOptions = (roles ?? []).map((r) => ({ value: r.name, label: r.name }));
  const userOptions = (users ?? []).map((u) => ({ value: u.username, label: u.display_name || u.username }));

  function fieldValid(key: string, fieldType: string): boolean {
    const raw = values[key] ?? "";
    if (fieldType === "money") return parseToMinor(raw) !== null && (parseToMinor(raw) ?? 0) > 0;
    if (fieldType === "number") return raw !== "" && Number(raw) > 0;
    return raw !== "";
  }

  const allValid = name.trim() !== "" && template.fields.every((f) => fieldValid(f.key, f.type));

  function summaryLine(key: string, fieldType: string, label: string): string {
    const raw = values[key] ?? "";
    if (!raw) return t("automations.summary.blank", { label });
    if (fieldType === "money") {
      const minor = parseToMinor(raw);
      return t("automations.summary.line", { label, value: minor !== null ? formatMinor(minor) : raw });
    }
    if (fieldType === "person") {
      const match = (users ?? []).find((u) => u.username === raw);
      return t("automations.summary.line", { label, value: match?.display_name || raw });
    }
    return t("automations.summary.line", { label, value: raw });
  }

  async function onSave() {
    setSaving(true);
    try {
      const params: Record<string, unknown> = {};
      for (const field of template!.fields) {
        params[field.key] =
          field.type === "money" ? parseToMinor(values[field.key] ?? "0") ?? 0
          : field.type === "number" ? Number(values[field.key] ?? 0)
          : values[field.key] ?? "";
      }
      const wf = await createFromTemplate(templateId as string, name, params);
      toast.show(t("automations.saved"), "success");
      navigate(`/workflows/${wf.id}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="automations template-form">
      <h1>{template.name[lang] ?? template.name.en}</h1>
      <label className="field">
        <span>{t("automations.title")}</span>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>

      {template.fields.map((field) => {
        const label = field.label[lang] ?? field.label.en;
        return (
          <label className="field" key={field.key}>
            <span>{label}</span>
            {field.type === "role" && (
              <ComboBox
                options={roleOptions}
                value={values[field.key] ?? ""}
                onChange={(v) => setValues((val) => ({ ...val, [field.key]: v }))}
                placeholder={t("automations.field.approverRolePlaceholder")}
              />
            )}
            {field.type === "person" && (
              <ComboBox
                options={userOptions}
                value={values[field.key] ?? ""}
                onChange={(v) => setValues((val) => ({ ...val, [field.key]: v }))}
                placeholder={t("automations.field.recipientPlaceholder")}
              />
            )}
            {field.type === "money" && (
              <input
                type="text"
                inputMode="decimal"
                placeholder="0.00"
                value={values[field.key] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
              />
            )}
            {field.type === "number" && (
              <input
                type="number"
                min={1}
                step={1}
                value={values[field.key] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
              />
            )}
          </label>
        );
      })}

      <div className="template-form__summary" role="status">
        <h2>{t("automations.summary.heading")}</h2>
        <p>{name ? t("automations.summary.name", { name }) : t("automations.summary.nameBlank")}</p>
        <ul>
          {template.fields.map((field) => (
            <li key={field.key}>{summaryLine(field.key, field.type, field.label[lang] ?? field.label.en)}</li>
          ))}
        </ul>
      </div>

      <button className="btn btn--primary" onClick={onSave} disabled={saving || !allValid}>
        {t("automations.save")}
      </button>
    </section>
  );
}
