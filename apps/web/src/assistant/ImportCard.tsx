import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  executeImport,
  previewImport,
  type ActionRecord,
  type ImportMapping,
  type ImportPreview,
  type ImportReport,
  type ImportReportRow,
  type ImportTask,
} from "../api/assistant";
import { NavIcon } from "../app/icons";
import { Bdi } from "../components/Bdi";
import { EntityLink } from "../components/EntityLink";

// Each import target's home-module icon (chrome stays monochrome; the icon just names the area).
const TARGET_ICON: Record<ImportTask["target"], string> = {
  customers: "crm",
  suppliers: "purchasing",
  items: "inventory",
};

// A created record link — imports only ever create customers/suppliers/items, each of which resolves
// through EntityLink by its business key (the narrow cast is safe: execute returns only these three).
function CreatedLink({ r, onNavigate }: { r: ActionRecord; onNavigate?: () => void }) {
  const icon = r.type === "supplier" ? "purchasing" : r.type === "item" ? "inventory" : "crm";
  const type = r.type as "customer" | "supplier" | "item";
  return (
    <EntityLink className="assistant-cite" type={type} value={r.value} onClick={onNavigate}>
      <NavIcon name={icon} />
      <Bdi>{r.label}</Bdi>
    </EntityLink>
  );
}

// One CSV cell — quote when it carries a comma, quote, or newline (double any inner quotes).
function csvCell(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

function downloadReport(rows: ImportReportRow[], filename: string) {
  const head = "row,status,key,message";
  const body = rows
    .map((r) => [r.row, r.status, csvCell(r.key), csvCell(r.message)].join(","))
    .join("\n");
  const uri = `data:text/csv;charset=utf-8,${encodeURIComponent(`${head}\n${body}`)}`;
  const a = document.createElement("a");
  a.href = uri;
  a.download = filename;
  a.click();
}

interface ImportCardProps {
  messageId: number;
  task: ImportTask;
  // Persist the settled/advanced card back onto its message so a reload shows the same stage.
  onResolved: (messageId: number, task: ImportTask) => void;
  onNavigate?: () => void;
}

/**
 * The spreadsheet the agent read, stepped through mapping → preview → report. The mapping and preview
 * stages are local (re-derivable, nothing written); Confirm runs the module contract row by row and
 * persists the report onto the message, so a reloaded thread shows the settled outcome — the same
 * reload-safety as a confirmed ActionCard.
 */
export function ImportCard({ messageId, task, onResolved, onNavigate }: ImportCardProps) {
  const { t } = useTranslation();
  const [mapping, setMapping] = useState<ImportMapping>(task.mapping);
  const [stage, setStage] = useState<"mapping" | "preview" | "report">(
    task.report ? "report" : "mapping",
  );
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [report, setReport] = useState<ImportReport | null>(task.report ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fieldLabel = (key: string) =>
    t(`assistant.import.fields.${key}`, task.fields.find((f) => f.key === key)?.label ?? key);
  const targetName = t(`assistant.import.target.${task.target}`, task.target);

  // A required field with no column chosen blocks the preview — the user must map it or fix the file.
  const missingRequired = task.fields.filter((f) => f.required && !mapping[f.key]);
  // Columns no field claims are ignored on import — named plainly so nothing silently vanishes.
  const ignored = task.columns.filter((c) => !Object.values(mapping).includes(c));

  async function runPreview() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const p = await previewImport(messageId, mapping);
      setPreview(p);
      setStage("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("assistant.errorLine"));
    } finally {
      setBusy(false);
    }
  }

  async function runExecute() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const r = await executeImport(messageId, mapping);
      setReport(r);
      setStage("report");
      onResolved(messageId, { ...task, mapping, stage: "report", report: r });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("assistant.errorLine"));
    } finally {
      setBusy(false);
    }
  }

  // --- report stage ----------------------------------------------------------------------------
  if (stage === "report" && report) {
    return (
      <div className="action-card action-card--done import-card">
        <p className="action-card__result">
          <NavIcon name="checkCircle" />
          {t("assistant.import.created", { count: report.created })}
          {report.skipped > 0 && ` · ${t("assistant.import.skipped", { count: report.skipped })}`}
        </p>
        {report.links.length > 0 && (
          <ul className="assistant-cites">
            {report.links.map((r) => (
              <li key={`${r.type}:${r.value}`}>
                <CreatedLink r={r} onNavigate={onNavigate} />
              </li>
            ))}
          </ul>
        )}
        <button
          type="button"
          className="action-card__dismiss import-card__report-link"
          onClick={() => downloadReport(report.report, `import-${task.target}.csv`)}
        >
          <NavIcon name="download" />
          {t("assistant.import.downloadReport")}
        </button>
      </div>
    );
  }

  // --- preview stage ---------------------------------------------------------------------------
  if (stage === "preview" && preview) {
    const skip = preview.errors.length + preview.duplicates.length;
    return (
      <div className="action-card import-card">
        <header className="action-card__head">
          <span className="action-card__icon" aria-hidden="true">
            <NavIcon name={TARGET_ICON[task.target]} />
          </span>
          <span className="action-card__title">{t("assistant.import.previewTitle")}</span>
        </header>

        <ul className="import-card__tallies">
          <li className="import-card__tally import-card__tally--ok">
            <NavIcon name="check" />
            {t("assistant.import.valid", { count: preview.valid })}
          </li>
          {preview.duplicates.length > 0 && (
            <li className="import-card__tally">
              <NavIcon name="duplicate" />
              {t("assistant.import.duplicates", { count: preview.duplicates.length })}
            </li>
          )}
          {preview.errors.length > 0 && (
            <li className="import-card__tally import-card__tally--bad">
              <NavIcon name="flag" />
              {t("assistant.import.errors", { count: preview.errors.length })}
            </li>
          )}
        </ul>

        {preview.rows.length > 0 && (
          <div className="import-card__table-wrap">
            <table className="import-card__table">
              <thead>
                <tr>
                  {task.fields.map((f) => (
                    <th key={f.key} scope="col">{fieldLabel(f.key)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row) => (
                  <tr key={row.row as number}>
                    {task.fields.map((f) => (
                      <td key={f.key} dir="auto">{row[f.key] ?? ""}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {preview.errors.length > 0 && (
          <ul className="import-card__issues">
            {preview.errors.map((e, i) => (
              <li key={i} dir="auto">
                {t("assistant.import.rowError", {
                  row: e.row,
                  field: fieldLabel(e.field),
                  message: e.message,
                })}
              </li>
            ))}
          </ul>
        )}

        {preview.duplicates.length > 0 && (
          <ul className="import-card__issues import-card__issues--muted">
            {preview.duplicates.map((d, i) => (
              <li key={i} dir="auto">
                {t("assistant.import.rowDuplicate", { row: d.row, key: d.key })}
              </li>
            ))}
          </ul>
        )}

        {error && <p className="action-card__error" dir="auto">{error}</p>}

        <footer className="action-card__foot">
          <button
            type="button"
            className="action-card__confirm"
            onClick={() => void runExecute()}
            disabled={busy || preview.valid === 0}
          >
            {busy
              ? t("common.loading")
              : t("assistant.import.confirmLine", { count: preview.valid, skip })}
          </button>
          <button
            type="button"
            className="action-card__dismiss"
            onClick={() => setStage("mapping")}
            disabled={busy}
          >
            {t("assistant.import.back")}
          </button>
        </footer>
      </div>
    );
  }

  // --- mapping stage ---------------------------------------------------------------------------
  return (
    <div className="action-card import-card">
      <header className="action-card__head">
        <span className="action-card__icon" aria-hidden="true">
          <NavIcon name={TARGET_ICON[task.target]} />
        </span>
        <span className="action-card__title">
          {t("assistant.import.mapTitle", { target: targetName })}
        </span>
        <span className="action-card__count">
          {t("assistant.import.rows", { count: task.row_count })}
        </span>
      </header>

      <ul className="import-card__map">
        {task.fields.map((f) => (
          <li key={f.key} className="import-card__map-row">
            <span className="import-card__field">
              {fieldLabel(f.key)}
              {f.required && <span className="import-card__req" aria-hidden="true">*</span>}
            </span>
            <select
              className="import-card__select"
              value={mapping[f.key] ?? ""}
              onChange={(e) =>
                setMapping((m) => ({ ...m, [f.key]: e.target.value || null }))
              }
            >
              <option value="">{t("assistant.import.ignore")}</option>
              {task.columns.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </li>
        ))}
      </ul>

      {ignored.length > 0 && (
        <p className="import-card__ignored" dir="auto">
          {t("assistant.import.ignoredColumns", { columns: ignored.join("، ") })}
        </p>
      )}

      {missingRequired.length > 0 && (
        <p className="action-card__error" dir="auto">
          {t("assistant.import.needsColumn", {
            fields: missingRequired.map((f) => fieldLabel(f.key)).join("، "),
          })}
        </p>
      )}

      {error && <p className="action-card__error" dir="auto">{error}</p>}

      <footer className="action-card__foot">
        <button
          type="button"
          className="action-card__confirm"
          onClick={() => void runPreview()}
          disabled={busy || missingRequired.length > 0}
        >
          {busy ? t("common.loading") : t("assistant.import.continue")}
        </button>
      </footer>
    </div>
  );
}
