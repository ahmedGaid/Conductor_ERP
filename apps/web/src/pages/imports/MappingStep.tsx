import { useState } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../../app/icons";
import { ApiError } from "../../api/client";
import {
  createImportProfile,
  entityLabelKey,
  postImportMapping,
  type ImportBatch,
  type ImportFieldSpec,
  type ImportMappingResult,
  type ImportProfileHit,
  type ImportUploadResult,
} from "../../api/smartImports";
import { useToast } from "../../app/ToastContext";

function confidenceWord(c: number): "high" | "medium" | "low" {
  if (c >= 90) return "high";
  if (c >= 50) return "medium";
  return "low";
}

function ConfidencePill({ confidence }: { confidence: number }) {
  const { t } = useTranslation();
  const word = confidenceWord(confidence);
  const icon = word === "high" ? "check" : word === "medium" ? "info" : "warning";
  return (
    <span className={`imports-confidence imports-confidence--${word}`}>
      <NavIcon name={icon} />
      {t(`imports.confidence.${word}`)}
    </span>
  );
}

function StatsSummary({ batch, entityLabel }: { batch: ImportBatch; entityLabel: string }) {
  const { t } = useTranslation();
  const stats = batch.stats;
  const newRefLines = Object.entries(stats.new_refs ?? {}).filter(([, vals]) => vals.length > 0);
  const issueTotal = Object.values(stats.issues_by_code ?? {}).reduce((a, b) => a + b, 0);

  return (
    <div className="imports-stats">
      <p className="imports-stats__headline" dir="auto">
        {t("imports.stats.rowsOf", { count: stats.rows ?? 0, entity: entityLabel })}
      </p>
      {newRefLines.length > 0 && (
        <ul className="imports-stats__list">
          {newRefLines.map(([entity, vals]) => (
            <li key={entity} dir="auto">
              {t("imports.stats.newRefs", {
                count: vals.length,
                suffix: vals.length >= 50 ? "+" : "",
                entity: t(entityLabelKey(entity), entity),
              })}
            </li>
          ))}
        </ul>
      )}
      {(issueTotal > 0 || (stats.duplicates_in_file ?? 0) > 0) && (
        <ul className="imports-stats__list imports-stats__list--muted">
          {issueTotal > 0 && <li dir="auto">{t("imports.stats.issues", { count: issueTotal })}</li>}
          {(stats.duplicates_in_file ?? 0) > 0 && (
            <li dir="auto">{t("imports.stats.duplicatesInFile", { count: stats.duplicates_in_file })}</li>
          )}
        </ul>
      )}
    </div>
  );
}

interface MapModeProps {
  upload: ImportUploadResult;
  entity: string;
  profile?: ImportProfileHit;
  batch?: undefined;
  onMapped: (result: ImportMappingResult) => void;
}

interface StatsModeProps {
  upload?: undefined;
  entity?: undefined;
  profile?: undefined;
  batch: ImportBatch;
  onMapped: (result: ImportMappingResult) => void;
}

export function MappingStep(props: MapModeProps | StatsModeProps) {
  if (props.batch) {
    const label = props.batch.entity; // resolved to a translated label below via entityLabelKey
    return <ResumedStats batch={props.batch} rawEntity={label} />;
  }
  return <InteractiveMapping {...props} />;
}

function ResumedStats({ batch, rawEntity }: { batch: ImportBatch; rawEntity: string }) {
  const { t } = useTranslation();
  return <StatsSummary batch={batch} entityLabel={t(entityLabelKey(rawEntity), rawEntity)} />;
}

function InteractiveMapping({ upload, entity, profile, onMapped }: MapModeProps) {
  const { t } = useTranslation();
  const toast = useToast();
  const fields: ImportFieldSpec[] = upload.entity_fields[entity] ?? [];
  const validFieldNames = new Set(fields.map((f) => f.name));
  const requiredFields = fields.filter((f) => f.required);
  const optionalFields = fields.filter((f) => !f.required);
  const fieldLabel = (name: string) => t(`imports.field.${name}`, name);
  const entityLabel = t(upload.candidates.find((c) => c.entity === entity)?.label_key ?? entityLabelKey(entity), entity);

  const [mapping, setMapping] = useState<Record<string, string>>(() => {
    if (profile) {
      // A saved profile can drift from the current file — a re-exported sheet with fewer/renamed
      // columns, or (defensively) a profile saved with a stale/invalid field. Only keep entries
      // whose column still exists in this upload and whose field is still valid for this entity;
      // anything else is silently dropped rather than poisoning the mapping the way an unfiltered
      // suggestion did (same failure mode as the mapping_suggestion path above).
      const headerSet = new Set(upload.headers);
      const inverted: Record<string, string> = {};
      for (const [field, column] of Object.entries(profile.mapping)) {
        if (validFieldNames.has(field) && headerSet.has(column)) inverted[column] = field;
      }
      return inverted;
    }
    // `upload.mapping_suggestion` is computed server-side against the *top detected candidate*
    // only (see UploadView) — when the user picks a different candidate from the chooser, a
    // suggested field may not exist on the chosen entity at all. Only seed fields the chosen
    // entity actually has; anything else silently becomes a phantom mapping that Continue's
    // POST would reject with an inscrutable "unknown fields" error.
    const initial: Record<string, string> = {};
    for (const [column, suggestion] of Object.entries(upload.mapping_suggestion)) {
      if (suggestion.field && validFieldNames.has(suggestion.field)) initial[column] = suggestion.field;
    }
    return initial;
  });
  const [profileName, setProfileName] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fieldToColumns = new Map<string, string[]>();
  for (const [column, field] of Object.entries(mapping)) {
    if (!field) continue;
    fieldToColumns.set(field, [...(fieldToColumns.get(field) ?? []), column]);
  }
  const missingRequired = requiredFields.filter((f) => !fieldToColumns.get(f.name)?.length);
  const duplicateFields = [...fieldToColumns.entries()].filter(([, cols]) => cols.length > 1);
  const ignoredColumns = upload.headers.filter((c) => !mapping[c]);

  function fieldToColumnMapping(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const [column, field] of Object.entries(mapping)) {
      if (field) out[field] = column;
    }
    return out;
  }

  async function onContinue() {
    if (busy || missingRequired.length > 0 || duplicateFields.length > 0) return;
    setBusy(true);
    setError(null);
    try {
      const result = await postImportMapping(upload.batch_id, entity, fieldToColumnMapping(), profile?.id);
      onMapped(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error.title"));
    } finally {
      setBusy(false);
    }
  }

  async function onSaveProfile() {
    const name = profileName.trim();
    if (!name || savingProfile) return;
    setSavingProfile(true);
    try {
      await createImportProfile(name, entity, fieldToColumnMapping());
      setProfileSaved(true);
      setProfileName("");
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t("common.error.title"), "error");
    } finally {
      setSavingProfile(false);
    }
  }

  return (
    <div className="imports-mapping">
      <h2 className="imports-mapping__title" dir="auto">
        {t("imports.mapping.title", { entity: entityLabel })}
      </h2>

      <div className="imports-mapping__table-wrap">
        <table className="imports-mapping__table">
          <thead>
            <tr>
              <th scope="col">{t("imports.mapping.columnHeader")}</th>
              <th scope="col">{t("imports.mapping.samplesHeader")}</th>
              <th scope="col">{t("imports.mapping.fieldHeader")}</th>
              <th scope="col">{t("imports.mapping.confidenceHeader")}</th>
            </tr>
          </thead>
          <tbody>
            {upload.headers.map((column) => {
              const suggestion = upload.mapping_suggestion[column];
              const samples = upload.samples.slice(0, 2).map((row) => row[column] ?? "");
              return (
                <tr key={column}>
                  <td dir="auto">{column}</td>
                  <td dir="auto" className="muted">{samples.join("، ")}</td>
                  <td>
                    <select
                      className="imports-mapping__select"
                      value={mapping[column] ?? ""}
                      onChange={(e) =>
                        setMapping((m) => ({ ...m, [column]: e.target.value }))
                      }
                    >
                      <option value="">{t("imports.mapping.ignore")}</option>
                      {requiredFields.length > 0 && (
                        <optgroup label={t("imports.mapping.requiredGroup")}>
                          {requiredFields.map((f) => (
                            <option key={f.name} value={f.name}>{fieldLabel(f.name)}</option>
                          ))}
                        </optgroup>
                      )}
                      {optionalFields.length > 0 && (
                        <optgroup label={t("imports.mapping.optionalGroup")}>
                          {optionalFields.map((f) => (
                            <option key={f.name} value={f.name}>{fieldLabel(f.name)}</option>
                          ))}
                        </optgroup>
                      )}
                    </select>
                  </td>
                  <td>
                    {suggestion?.field && validFieldNames.has(suggestion.field) ? (
                      <ConfidencePill confidence={suggestion.confidence} />
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {ignoredColumns.length > 0 && (
        <p className="imports-mapping__note muted" dir="auto">
          {t("imports.mapping.ignoredNote", { columns: ignoredColumns.join("، ") })}
        </p>
      )}

      {duplicateFields.length > 0 && (
        <p className="imports-mapping__notice" dir="auto" role="alert">
          {t("imports.mapping.duplicateField", {
            fields: duplicateFields.map(([f]) => fieldLabel(f)).join("، "),
          })}
        </p>
      )}

      {missingRequired.length > 0 && (
        <p className="imports-mapping__notice" dir="auto" role="alert">
          {t("imports.mapping.requiredGap", { fields: missingRequired.map((f) => fieldLabel(f.name)).join("، ") })}
        </p>
      )}

      {error && <p className="imports-mapping__notice" dir="auto" role="alert">{error}</p>}

      <div className="imports-mapping__save-profile">
        <input
          type="text"
          className="imports-mapping__save-profile-input"
          placeholder={t("imports.mapping.saveProfilePlaceholder")}
          value={profileName}
          onChange={(e) => {
            setProfileName(e.target.value);
            setProfileSaved(false);
          }}
        />
        <button
          type="button"
          className="btn btn--ghost"
          disabled={!profileName.trim() || savingProfile}
          onClick={() => void onSaveProfile()}
        >
          {savingProfile ? t("common.loading") : profileSaved ? t("imports.mapping.saveProfileSaved") : t("imports.mapping.saveProfileButton")}
        </button>
      </div>

      <footer className="imports-mapping__foot">
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => void onContinue()}
          disabled={busy || missingRequired.length > 0 || duplicateFields.length > 0}
        >
          {busy ? t("common.loading") : t("imports.mapping.continue")}
        </button>
      </footer>
    </div>
  );
}
