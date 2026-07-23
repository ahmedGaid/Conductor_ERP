import { useState } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../../app/icons";
import { Bdi } from "../../components/Bdi";
import { DatePicker } from "../../components/DatePicker";
import { EmptyState } from "../../components/EmptyState";
import { formatMinor, minorToAmount, parseToMinor } from "../../lib/money";
import type { ImportFieldSpec, ImportIssue, ImportRowRow } from "../../api/smartImports";

const STATUS_ICON: Record<string, string> = {
  valid: "check",
  imported: "check",
  error: "warning",
  duplicate: "duplicate",
  skipped: "archive",
  pending: "info",
};

function displayValue(field: ImportFieldSpec, value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  if (field.kind === "money" && typeof value === "number") return formatMinor(value);
  return String(value);
}

function editValue(field: ImportFieldSpec, value: unknown): string {
  if (value === null || value === undefined) return "";
  if (field.kind === "money" && typeof value === "number") return minorToAmount(value);
  return String(value);
}

function parseEdit(field: ImportFieldSpec, raw: string): unknown {
  if (field.kind === "money") return parseToMinor(raw) ?? 0;
  if (field.kind === "number") {
    const n = Number(raw);
    return Number.isFinite(n) ? n : raw;
  }
  return raw;
}

function fieldIssue(issues: ImportIssue[], fieldName: string): ImportIssue | undefined {
  return issues.find((i) => i.field === fieldName && i.code !== "duplicate_in_file" && i.code !== "probable_duplicate");
}

interface EditCellProps {
  field: ImportFieldSpec;
  value: unknown;
  issue: ImportIssue | undefined;
  onSave: (value: unknown) => void;
  onGoToPlan: () => void;
}

function EditCell({ field, value, issue, onSave, onGoToPlan }: EditCellProps) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(() => editValue(field, value));

  if (issue?.code === "missing_ref") {
    return (
      <button type="button" className="imports-grid__ref-chip" onClick={onGoToPlan}>
        <NavIcon name="info" />
        {t("imports.issues.missingRefChip", { value: String(value ?? issue.meta?.value ?? "") })}
      </button>
    );
  }

  if (editing) {
    if (field.kind === "date") {
      return (
        <DatePicker
          value={typeof value === "string" ? value : ""}
          onChange={(v) => {
            setEditing(false);
            onSave(v);
          }}
        />
      );
    }
    return (
      <input
        type={field.kind === "number" || field.kind === "money" ? "text" : "text"}
        className="imports-grid__edit-input"
        value={draft}
        autoFocus
        dir="auto"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => {
          setEditing(false);
          const parsed = parseEdit(field, draft);
          if (parsed !== value) onSave(parsed);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
          if (e.key === "Escape") {
            setDraft(editValue(field, value));
            setEditing(false);
          }
        }}
      />
    );
  }

  return (
    <button
      type="button"
      className={issue ? "imports-grid__cell imports-grid__cell--issue" : "imports-grid__cell"}
      title={issue ? t(issue.message, { defaultValue: issue.code }) : undefined}
      onClick={() => {
        setDraft(editValue(field, value));
        setEditing(true);
      }}
    >
      <Bdi>{displayValue(field, value) || <span className="muted">—</span>}</Bdi>
      {issue && <span className="imports-grid__issue-dot" aria-hidden="true" />}
    </button>
  );
}

export function PreviewGrid({
  fields,
  rows,
  busyRows,
  onEditCell,
  onGoToPlan,
}: {
  fields: ImportFieldSpec[];
  rows: ImportRowRow[];
  busyRows: Set<number>;
  onEditCell: (rowNumber: number, field: string, value: unknown) => void;
  onGoToPlan: () => void;
}) {
  const { t } = useTranslation();

  if (rows.length === 0) {
    return (
      <EmptyState
        icon={<NavIcon name="check" />}
        title={t("imports.review.emptyTab.title")}
        hint={t("imports.review.emptyTab.hint")}
      />
    );
  }

  return (
    <div className="imports-grid__wrap">
      <table className="imports-grid__table">
        <thead>
          <tr>
            <th scope="col" className="imports-grid__row-col">{t("imports.review.rowHeader")}</th>
            {fields.map((f) => (
              <th key={f.name} scope="col">{t(`imports.field.${f.name}`, f.name)}</th>
            ))}
            <th scope="col">{t("imports.review.statusHeader")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.row_number} className={busyRows.has(row.row_number) ? "imports-grid__row--busy" : undefined}>
              <td className="imports-grid__row-col muted">{row.row_number}</td>
              {fields.map((f) => (
                <td key={f.name}>
                  <EditCell
                    field={f}
                    value={row.normalized[f.name]}
                    issue={fieldIssue(row.issues, f.name)}
                    onSave={(v) => onEditCell(row.row_number, f.name, v)}
                    onGoToPlan={onGoToPlan}
                  />
                </td>
              ))}
              <td>
                <span className={`imports-grid__status imports-grid__status--${row.status}`}>
                  <NavIcon name={STATUS_ICON[row.status] ?? "info"} />
                  {t(`imports.review.status.${row.status}`, row.status)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
