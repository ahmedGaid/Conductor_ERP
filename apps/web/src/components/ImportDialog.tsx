import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  downloadImportTemplate,
  runImport,
  type ImportFieldInfo,
  type ImportResult,
} from "../api/imports";
import { useToast } from "../app/ToastContext";
import "../app/CommandPalette.css";
import "./ImportDialog.css";

interface Props {
  open: boolean;
  onClose: () => void;
  /** API base for the list, e.g. "/sales/customers". */
  basePath: string;
  title: string;
  templateName: string;
  /** Canonical columns the import targets (label already translated). */
  fields: ImportFieldInfo[];
  /** Called after a successful commit so the list can refresh. */
  onCommitted: (result: ImportResult) => void;
}

/**
 * Reusable CSV import: upload -> map columns -> preview -> confirm. Preview and commit hit the same
 * server engine, so the preview is exactly what commit will do. Built on the command-palette native
 * <dialog> shell (top layer, focus trap, Esc), monochrome chrome with status only inside the work.
 */
export function ImportDialog({ open, onClose, basePath, title, templateName, fields, onCommitted }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [mode, setMode] = useState<"create" | "upsert">("create");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    if (open && !dlg.open) dlg.showModal();
    else if (!open && dlg.open) dlg.close();
  }, [open]);

  // Reset everything when the dialog is dismissed, so the next open starts clean.
  function reset() {
    setFile(null);
    setResult(null);
    setMapping({});
    setMode("create");
    setBusy(false);
    setError(null);
  }
  function close() {
    reset();
    onClose();
  }

  async function preview(f: File, nextMapping?: Record<string, string>, nextMode?: "create" | "upsert") {
    setBusy(true);
    setError(null);
    try {
      const res = await runImport(basePath, f, {
        mapping: nextMapping,
        mode: nextMode ?? mode,
        commit: false,
      });
      setResult(res);
      // Seed the editable mapping from the server's auto-match on the first preview.
      setMapping(nextMapping ?? res.mapping);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  function onPickFile(f: File | null) {
    if (!f) return;
    setFile(f);
    void preview(f);
  }

  function changeMapping(fieldName: string, header: string) {
    const next = { ...mapping };
    if (header) next[fieldName] = header;
    else delete next[fieldName];
    setMapping(next);
    if (file) void preview(file, next);
  }

  function changeMode(next: "create" | "upsert") {
    setMode(next);
    if (file) void preview(file, mapping, next);
  }

  async function commit() {
    if (!file || !result) return;
    setBusy(true);
    setError(null);
    try {
      const res = await runImport(basePath, file, { mapping, mode, commit: true });
      const applied = res.summary.created + res.summary.updated;
      toast.show(t("import.toast.done", { count: applied }), "success");
      onCommitted(res);
      close();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const unmappedRequired = fields.filter((f) => f.required && !mapping[f.name]);
  const applyCount = result ? result.summary.created + result.summary.updated : 0;
  const failedRows = result ? result.rows.filter((r) => r.outcome === "failed") : [];

  function onBackdropClick(e: React.MouseEvent) {
    if (e.target === dialogRef.current) close();
  }

  return (
    <dialog
      ref={dialogRef}
      className="cmdp"
      aria-label={title}
      onClose={close}
      onCancel={close}
      onClick={onBackdropClick}
    >
      <div className="cmdp__panel import">
        <header className="import__head">
          <h2 className="import__title">{title}</h2>
          <button type="button" className="btn btn--ghost btn--sm" onClick={close} aria-label={t("common.close")}>
            {t("common.close")}
          </button>
        </header>

        <div className="import__body">
          {/* Step 1 — choose a file (with a template to make columns obvious). */}
          {!result && (
            <div className="import__upload">
              <p className="import__lede">{t("import.upload.lede")}</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                className="import__file"
                onChange={(e) => onPickFile(e.target.files?.[0] ?? null)}
              />
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => fileInputRef.current?.click()}
                disabled={busy}
              >
                {busy ? t("common.loading") : t("import.upload.choose")}
              </button>
              <button
                type="button"
                className="import__template-link"
                onClick={() => void downloadImportTemplate(basePath, templateName)}
              >
                {t("import.upload.template")}
              </button>
            </div>
          )}

          {/* Step 2 — map columns + live preview + confirm. */}
          {result && (
            <>
              <section className="import__section">
                <h3 className="import__section-title">{t("import.map.title")}</h3>
                <p className="import__hint">{t("import.map.hint", { file: file?.name ?? "" })}</p>
                <ul className="import__map">
                  {fields.map((f) => (
                    <li key={f.name} className="import__map-row">
                      <span className="import__map-label">
                        {f.label}
                        {f.required && <span className="import__req" aria-hidden="true"> *</span>}
                      </span>
                      <select
                        className="import__map-select"
                        value={mapping[f.name] ?? ""}
                        onChange={(e) => changeMapping(f.name, e.target.value)}
                      >
                        <option value="">{t("import.map.ignore")}</option>
                        {result.headers.map((h) => (
                          <option key={h} value={h}>{h}</option>
                        ))}
                      </select>
                    </li>
                  ))}
                </ul>
                {unmappedRequired.length > 0 && (
                  <p className="import__warn">
                    {t("import.map.missingRequired", {
                      fields: unmappedRequired.map((f) => f.label).join("، "),
                    })}
                  </p>
                )}
              </section>

              <section className="import__section">
                <div className="import__mode">
                  <span className="import__section-title">{t("import.mode.title")}</span>
                  <label className="import__radio">
                    <input
                      type="radio"
                      name="import-mode"
                      checked={mode === "create"}
                      onChange={() => changeMode("create")}
                    />
                    <span>{t("import.mode.create")}</span>
                  </label>
                  <label className="import__radio">
                    <input
                      type="radio"
                      name="import-mode"
                      checked={mode === "upsert"}
                      onChange={() => changeMode("upsert")}
                    />
                    <span>{t("import.mode.upsert")}</span>
                  </label>
                </div>
              </section>

              <section className="import__section">
                <h3 className="import__section-title">{t("import.preview.title")}</h3>
                <ul className="import__summary">
                  <SummaryChip n={result.summary.created} label={t("import.outcome.created")} tone="ok" />
                  {result.summary.updated > 0 && (
                    <SummaryChip n={result.summary.updated} label={t("import.outcome.updated")} tone="ok" />
                  )}
                  <SummaryChip n={result.summary.skipped} label={t("import.outcome.skipped")} tone="muted" />
                  <SummaryChip n={result.summary.failed} label={t("import.outcome.failed")} tone="bad" />
                </ul>

                {failedRows.length > 0 && (
                  <div className="import__errors">
                    <table className="import__error-table">
                      <thead>
                        <tr>
                          <th>{t("import.error.row")}</th>
                          <th>{t("import.error.field")}</th>
                          <th>{t("import.error.message")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {failedRows.slice(0, 50).map((r) =>
                          r.errors.map((e, i) => (
                            <tr key={`${r.row}-${i}`}>
                              <td className="latin">{r.row}</td>
                              <td>{fieldLabel(fields, e.field)}</td>
                              <td>{e.message}</td>
                            </tr>
                          )),
                        )}
                      </tbody>
                    </table>
                    {failedRows.length > 50 && (
                      <p className="import__hint">{t("import.error.more", { count: failedRows.length - 50 })}</p>
                    )}
                  </div>
                )}
              </section>
            </>
          )}

          {error && <p className="import__error-banner">{error}</p>}
        </div>

        {result && (
          <footer className="import__foot">
            <button type="button" className="btn" onClick={reset} disabled={busy}>
              {t("import.changeFile")}
            </button>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => void commit()}
              disabled={busy || applyCount === 0 || unmappedRequired.length > 0}
            >
              {applyCount > 0
                ? t("import.confirm", { count: applyCount })
                : t("import.confirmNone")}
            </button>
          </footer>
        )}
      </div>
    </dialog>
  );
}

function SummaryChip({ n, label, tone }: { n: number; label: string; tone: "ok" | "muted" | "bad" }) {
  return (
    <li className={`import__chip import__chip--${tone}`}>
      <span className="import__chip-n latin">{n}</span>
      <span className="import__chip-label">{label}</span>
    </li>
  );
}

function fieldLabel(fields: ImportFieldInfo[], name: string): string {
  return fields.find((f) => f.name === name)?.label ?? name;
}
