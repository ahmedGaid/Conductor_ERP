import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { getMe } from "../../api/identity";
import {
  createCustomFieldDef,
  deactivateCustomFieldDef,
  listCustomFieldDefs,
  updateCustomFieldDef,
  type CustomFieldDef,
  type CustomFieldEntity,
  type CustomFieldType,
} from "../../api/customFields";
import { useAsync } from "../../hooks/useAsync";
import { useFormKeys } from "../../hooks/useFormKeys";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { ErrorState } from "../../components/ErrorState";
import { EmptyState } from "../../components/EmptyState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { SegmentedControl } from "../../components/SegmentedControl";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import { SYSTEM_ADMIN } from "./roles";
import { Toggle } from "./controls";
import "../admin/admin.css";

const TYPES: CustomFieldType[] = ["TEXT", "NUMBER", "DATE", "CHOICE", "MONEY"];

function parseChoices(text: string): string[] {
  return text
    .split(",")
    .map((c) => c.trim())
    .filter(Boolean);
}

export function CustomFieldsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data: me } = useAsync(getMe, []);
  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;

  const [entity, setEntity] = useState<CustomFieldEntity>("sales.customer");
  const { data, loading, error, errorStatus, reload, mutate } = useAsync(
    () => listCustomFieldDefs(entity),
    [entity],
    `settings:customFields:${entity}`,
  );

  const [key, setKey] = useState("");
  const [labelAr, setLabelAr] = useState("");
  const [labelEn, setLabelEn] = useState("");
  const [type, setType] = useState<CustomFieldType>("TEXT");
  const [required, setRequired] = useState(false);
  const [choicesText, setChoicesText] = useState("");
  const formRef = useRef<HTMLFormElement>(null);
  useFormKeys({ formRef });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editLabelAr, setEditLabelAr] = useState("");
  const [editLabelEn, setEditLabelEn] = useState("");
  const [editType, setEditType] = useState<CustomFieldType>("TEXT");
  const [editRequired, setEditRequired] = useState(false);
  const [editChoicesText, setEditChoicesText] = useState("");

  const [deactivateTarget, setDeactivateTarget] = useState<CustomFieldDef | null>(null);

  if (me && !isAdmin) {
    return (
      <section className="page-enter">
        <SettingsNav />
        <div className="card setcard">
          <p className="muted">{t("settings.customFields.adminOnly")}</p>
        </div>
      </section>
    );
  }
  if (!me || loading) return <SettingsSkeleton />;

  function resetCreateForm() {
    setKey("");
    setLabelAr("");
    setLabelEn("");
    setType("TEXT");
    setRequired(false);
    setChoicesText("");
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const k = key.trim();
    const ar = labelAr.trim();
    const en = labelEn.trim();
    if (!k || !ar || !en) return;
    const position = (data ?? []).length;
    void runOptimistic<CustomFieldDef[], CustomFieldDef>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows,
      request: () =>
        createCustomFieldDef({
          entity_key: entity,
          key: k,
          label_ar: ar,
          label_en: en,
          type,
          required,
          choices: type === "CHOICE" ? parseChoices(choicesText) : [],
          position,
        }),
      settle: (rows, created) => [...rows, created],
      toast,
      success: t("settings.customFields.toastCreated"),
    });
    resetCreateForm();
  }

  function startEdit(def: CustomFieldDef) {
    setEditingId(def.id);
    setEditLabelAr(def.label_ar);
    setEditLabelEn(def.label_en);
    setEditType(def.type);
    setEditRequired(def.required);
    setEditChoicesText(def.choices.join(", "));
  }

  async function saveEdit(def: CustomFieldDef) {
    const ar = editLabelAr.trim();
    const en = editLabelEn.trim();
    if (!ar || !en) return;
    try {
      const updated = await updateCustomFieldDef(def.id, {
        label_ar: ar,
        label_en: en,
        type: editType,
        required: editRequired,
        choices: editType === "CHOICE" ? parseChoices(editChoicesText) : [],
      });
      mutate((data ?? []).map((d) => (d.id === updated.id ? updated : d)));
      setEditingId(null);
      toast.show(t("settings.customFields.toastUpdated"), "success");
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    }
  }

  function deactivate(def: CustomFieldDef) {
    void runOptimistic<CustomFieldDef[], CustomFieldDef>({
      current: data ?? [],
      mutate,
      optimistic: (rows) => rows.filter((d) => d.id !== def.id),
      request: () => deactivateCustomFieldDef(def.id),
      toast,
      success: t("settings.customFields.toastDeactivated"),
    });
  }

  async function move(def: CustomFieldDef, delta: number) {
    const rows = data ?? [];
    const i = rows.findIndex((d) => d.id === def.id);
    const j = i + delta;
    if (i < 0 || j < 0 || j >= rows.length) return;
    const other = rows[j];
    try {
      const [a, b] = await Promise.all([
        updateCustomFieldDef(def.id, { position: other.position }),
        updateCustomFieldDef(other.id, { position: def.position }),
      ]);
      const next = [...rows];
      next[i] = a.id === def.id ? a : b;
      next[j] = b.id === other.id ? b : a;
      next.sort((x, y) => x.position - y.position || x.key.localeCompare(y.key));
      mutate(next);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    }
  }

  return (
    <section className="page-enter">
      <SettingsNav />
      <p className="setrow__desc setcard__lead">{t("settings.customFields.lead")}</p>

      <SegmentedControl
        value={entity}
        onChange={setEntity}
        ariaLabel={t("settings.customFields.entityPicker")}
        options={[
          { value: "sales.customer", label: t("settings.customFields.entityCustomers") },
          { value: "inventory.item", label: t("settings.customFields.entityItems") },
          { value: "purchasing.supplier", label: t("settings.customFields.entitySuppliers") },
        ]}
      />

      <form ref={formRef} className="card admin-invite" onSubmit={onSubmit}>
        <div className="admin-invite__grid">
          <label className="admin-field">
            <span>{t("settings.customFields.key")}</span>
            <input
              className="latin"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              pattern="[a-z][a-z0-9_]*"
              title={t("settings.customFields.keyHint")}
              required
            />
          </label>
          <label className="admin-field">
            <span>{t("settings.customFields.labelAr")}</span>
            <input value={labelAr} onChange={(e) => setLabelAr(e.target.value)} dir="rtl" required />
          </label>
          <label className="admin-field">
            <span>{t("settings.customFields.labelEn")}</span>
            <input value={labelEn} onChange={(e) => setLabelEn(e.target.value)} dir="ltr" required />
          </label>
          <label className="admin-field">
            <span>{t("settings.customFields.type")}</span>
            <select value={type} onChange={(e) => setType(e.target.value as CustomFieldType)}>
              {TYPES.map((ty) => (
                <option key={ty} value={ty}>
                  {t(`settings.customFields.types.${ty}`)}
                </option>
              ))}
            </select>
          </label>
          {type === "CHOICE" && (
            <label className="admin-field">
              <span>{t("settings.customFields.choices")}</span>
              <input
                className="latin"
                value={choicesText}
                onChange={(e) => setChoicesText(e.target.value)}
                placeholder={t("settings.customFields.choicesPlaceholder")}
              />
            </label>
          )}
          <label className="admin-field">
            <span>{t("settings.customFields.required")}</span>
            <Toggle checked={required} onChange={setRequired} label={t("settings.customFields.required")} />
          </label>
        </div>
        <div className="admin-invite__foot">
          <button className="btn btn--primary" type="submit">
            {t("settings.customFields.add")}
          </button>
        </div>
      </form>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} status={errorStatus} />}

      {data && data.length === 0 && (
        <EmptyState title={t("settings.customFields.empty")} hint={t("settings.customFields.emptyHint")} />
      )}

      {data && data.length > 0 && (
        <div className="card admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t("settings.customFields.key")}</th>
                <th>{t("settings.customFields.labelAr")}</th>
                <th>{t("settings.customFields.labelEn")}</th>
                <th>{t("settings.customFields.type")}</th>
                <th>{t("settings.customFields.required")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((def, i) =>
                editingId === def.id ? (
                  <tr key={def.id} className="admin-row">
                    <td className="latin muted">{def.key}</td>
                    <td>
                      <input value={editLabelAr} onChange={(e) => setEditLabelAr(e.target.value)} dir="rtl" />
                    </td>
                    <td>
                      <input value={editLabelEn} onChange={(e) => setEditLabelEn(e.target.value)} dir="ltr" />
                    </td>
                    <td>
                      <select value={editType} onChange={(e) => setEditType(e.target.value as CustomFieldType)}>
                        {TYPES.map((ty) => (
                          <option key={ty} value={ty}>
                            {t(`settings.customFields.types.${ty}`)}
                          </option>
                        ))}
                      </select>
                      {editType === "CHOICE" && (
                        <input
                          className="latin"
                          value={editChoicesText}
                          onChange={(e) => setEditChoicesText(e.target.value)}
                          placeholder={t("settings.customFields.choicesPlaceholder")}
                        />
                      )}
                    </td>
                    <td>
                      <Toggle
                        checked={editRequired}
                        onChange={setEditRequired}
                        label={t("settings.customFields.required")}
                      />
                    </td>
                    <td className="webhook-row-actions">
                      <button className="btn btn--sm btn--primary" type="button" onClick={() => void saveEdit(def)}>
                        {t("settings.customFields.save")}
                      </button>
                      <button className="btn btn--ghost" type="button" onClick={() => setEditingId(null)}>
                        {t("common.cancel")}
                      </button>
                    </td>
                  </tr>
                ) : (
                  <tr key={def.id} className="admin-row">
                    <td className="latin">{def.key}</td>
                    <td>{def.label_ar}</td>
                    <td className="latin">{def.label_en}</td>
                    <td>{t(`settings.customFields.types.${def.type}`)}</td>
                    <td>{def.required ? t("common.yes") : t("common.no")}</td>
                    <td className="webhook-row-actions">
                      <button
                        className="btn btn--ghost btn--icon"
                        type="button"
                        aria-label={t("settings.dashboard.moveUp")}
                        disabled={i === 0}
                        onClick={() => void move(def, -1)}
                      >
                        <span aria-hidden="true">↑</span>
                      </button>
                      <button
                        className="btn btn--ghost btn--icon"
                        type="button"
                        aria-label={t("settings.dashboard.moveDown")}
                        disabled={i === data.length - 1}
                        onClick={() => void move(def, 1)}
                      >
                        <span aria-hidden="true">↓</span>
                      </button>
                      <button className="btn btn--ghost" type="button" onClick={() => startEdit(def)}>
                        {t("settings.customFields.edit")}
                      </button>
                      <button className="btn btn--ghost" type="button" onClick={() => setDeactivateTarget(def)}>
                        {t("settings.customFields.deactivate")}
                      </button>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        open={deactivateTarget !== null}
        title={t("settings.customFields.deactivateConfirmTitle")}
        body={t("settings.customFields.deactivateConfirmBody")}
        confirmLabel={t("settings.customFields.deactivate")}
        danger
        onConfirm={() => {
          if (deactivateTarget) deactivate(deactivateTarget);
        }}
        onClose={() => setDeactivateTarget(null)}
      />
    </section>
  );
}
