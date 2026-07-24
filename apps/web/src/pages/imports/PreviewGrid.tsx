import { Fragment, useState } from "react";
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

// Worst-first priority for a group's collective status chip — reuses the same status vocabulary
// as every per-row dot (FILE_15 CONFIRMED SCOPE: "reusing the existing STATUS_ICON/status-color
// vocabulary").
const STATUS_PRIORITY = ["error", "duplicate", "pending", "valid", "skipped", "imported"] as const;

function worstStatus(rows: ImportRowRow[]): string {
  for (const s of STATUS_PRIORITY) {
    if (rows.some((r) => r.status === s)) return s;
  }
  return rows[0]?.status ?? "pending";
}

function groupRowsById(rows: ImportRowRow[]): Map<string, ImportRowRow[]> {
  const map = new Map<string, ImportRowRow[]>();
  for (const row of rows) {
    const gid = row.group_meta?.group_id;
    if (!gid) continue;
    const list = map.get(gid);
    if (list) list.push(row);
    else map.set(gid, [row]);
  }
  return map;
}

function GroupHeaderRow({
  fields, headerFields, groupRows, colSpan,
}: {
  fields: ImportFieldSpec[];
  headerFields: string[];
  groupRows: ImportRowRow[];
  colSpan: number;
}) {
  const { t } = useTranslation();
  const meta = groupRows[0]?.group_meta;
  if (!meta) return null;

  const allIssues = groupRows.flatMap((r) => r.issues);
  const missingKey = allIssues.find((i) => i.code === "missing_group_key");
  const inconsistent = allIssues.find((i) => i.code === "inconsistent_document");
  const mismatch = allIssues.find((i) => i.code === "total_mismatch");

  let tone: string;
  let label: string;
  if (missingKey) {
    tone = "error";
    label = t("imports.issues.missingGroupKey");
  } else if (inconsistent) {
    tone = "error";
    label = t("imports.issues.inconsistentDocument", { field: t(`imports.field.${inconsistent.field}`, inconsistent.field) });
  } else if (mismatch) {
    tone = "duplicate"; // reuses the existing orange/warning tone
    label = t("imports.issues.totalMismatch");
  } else {
    tone = worstStatus(groupRows);
    label = t(`imports.review.status.${tone}`, tone);
  }

  return (
    <tr className={`imports-grid__group-row imports-grid__group-row--${tone}`}>
      <td colSpan={colSpan} className="imports-grid__group-cell">
        {headerFields
          .filter((name) => name !== "file_total_minor")
          .map((name) => {
            const field = fields.find((f) => f.name === name);
            const value = meta.header[name];
            if (!field || value === undefined || value === null || value === "") return null;
            return (
              <span key={name} className="imports-grid__group-field">
                <span className="muted">{t(`imports.field.${name}`, name)}:</span>{" "}
                <Bdi>{displayValue(field, value)}</Bdi>
              </span>
            );
          })}
        <span className="imports-grid__group-field">
          <span className="muted">{t("imports.review.group.lines", { count: meta.line_count })}</span>
        </span>
        {meta.computed_total_minor !== null && (
          <span className="imports-grid__group-total">
            <Bdi>{formatMinor(meta.computed_total_minor)}</Bdi>
            {mismatch?.meta?.file_total_minor !== undefined && (
              <s className="muted">{formatMinor(Number(mismatch.meta.file_total_minor))}</s>
            )}
          </span>
        )}
        <span className={`imports-grid__status imports-grid__status--${tone}`}>
          <NavIcon name={STATUS_ICON[tone] ?? "info"} />
          {label}
        </span>
      </td>
    </tr>
  );
}

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
      title={issue ? t(issue.message, { defaultValue: issue.code }) : t("imports.review.editableHint")}
      onClick={() => {
        setDraft(editValue(field, value));
        setEditing(true);
      }}
    >
      <Bdi>{displayValue(field, value) || <span className="muted">—</span>}</Bdi>
      {issue && <span className="imports-grid__issue-dot" aria-hidden="true" />}
      <span className="imports-grid__cell-edit-icon">
        <NavIcon name="edit" />
      </span>
    </button>
  );
}

export function PreviewGrid({
  fields,
  headerFields = [],
  rows,
  busyRows,
  onEditCell,
  onGoToPlan,
}: {
  fields: ImportFieldSpec[];
  headerFields?: string[];
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

  // Grouped (document) entities: header fields (doc number, party, date…) move into the group's
  // own tinted header row instead of repeating as mostly-blank per-line columns (FILE_15
  // CONFIRMED SCOPE). Ungrouped entities: zero change — `headerFields` is always empty for them.
  const grouped = headerFields.length > 0;
  const lineFields = grouped ? fields.filter((f) => !headerFields.includes(f.name)) : fields;
  const groupsById = grouped ? groupRowsById(rows) : null;
  const colSpan = lineFields.length + 2;

  return (
    <>
      <p className="imports-grid__hint">
        <NavIcon name="edit" />
        {t("imports.review.editableHint")}
      </p>
      <div className="imports-grid__wrap">
      <table className="imports-grid__table">
        <thead>
          <tr>
            <th scope="col" className="imports-grid__row-col">{t("imports.review.rowHeader")}</th>
            {lineFields.map((f) => (
              <th key={f.name} scope="col">{t(`imports.field.${f.name}`, f.name)}</th>
            ))}
            <th scope="col">{t("imports.review.statusHeader")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const gid = row.group_meta?.group_id;
            const showGroupHeader = grouped && row.group_meta?.is_first && gid && groupsById;
            return (
              <Fragment key={row.row_number}>
                {showGroupHeader && (
                  <GroupHeaderRow
                    key={`${gid}-header`}
                    fields={fields}
                    headerFields={headerFields}
                    groupRows={groupsById.get(gid) ?? [row]}
                    colSpan={colSpan}
                  />
                )}
                <tr key={row.row_number} className={busyRows.has(row.row_number) ? "imports-grid__row--busy" : undefined}>
                  <td className="imports-grid__row-col muted">{row.row_number}</td>
                  {lineFields.map((f) => (
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
              </Fragment>
            );
          })}
        </tbody>
      </table>
      </div>
    </>
  );
}
