import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { listTemplates, createFromTemplate, type WorkflowTemplate } from "../../api/workflowTemplates";
import "./AutomationsPage.css";

export function TemplateFormPage() {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { templateId } = useParams<{ templateId: string }>();
  const { data: templates, loading } = useAsync<WorkflowTemplate[]>(() => listTemplates(), []);
  const template = templates?.find((tpl) => tpl.id === templateId);
  const lang = i18n.language as "ar" | "en";
  const [name, setName] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  if (loading || !template) return null;

  async function onSave() {
    setSaving(true);
    try {
      const params: Record<string, unknown> = {};
      for (const field of template!.fields) {
        params[field.key] = field.type === "money" || field.type === "number"
          ? Number(values[field.key] ?? 0)
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
    <section className="automations">
      <h1>{template.name[lang] ?? template.name.en}</h1>
      <label className="field">
        <span>{t("automations.title")}</span>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>
      {template.fields.map((field) => (
        <label className="field" key={field.key}>
          <span>{field.label[lang] ?? field.label.en}</span>
          <input
            value={values[field.key] ?? ""}
            onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
          />
        </label>
      ))}
      <button className="btn btn--primary" onClick={onSave} disabled={saving || !name}>
        {t("automations.save")}
      </button>
    </section>
  );
}
