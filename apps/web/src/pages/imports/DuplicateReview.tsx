import { useTranslation } from "react-i18next";

import { NavIcon } from "../../app/icons";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { formatMinor } from "../../lib/money";
import type { ImportFieldSpec, ImportIssueCandidate, ImportRowRow } from "../../api/smartImports";

// "Apply to all like this" (spec Task C) is a deliberate v1 cut: grouping "like this" needs a
// second similarity pass across decisions themselves, and one wrong bulk-merge is exactly the
// kind of silent damage this screen exists to prevent. Every row gets its own explicit decision —
// slower for a big messy file, but never a surprise (Linear test: fewer, safer interactions).

function similarityWord(score: number): "veryLikely" | "likely" | "possible" {
  if (score >= 95) return "veryLikely";
  if (score >= 90) return "likely";
  return "possible";
}

function rowLabel(row: ImportRowRow, nameField: string | undefined): string {
  if (!nameField) return String(row.row_number);
  return String(row.normalized[nameField] ?? row.row_number);
}

export function DuplicateReview({
  rows,
  nameField,
  headerFields = [],
  busyRows,
  onDecide,
}: {
  rows: ImportRowRow[];
  nameField: string | undefined;
  fields: ImportFieldSpec[];
  headerFields?: string[];
  busyRows: Set<number>;
  onDecide: (rowNumber: number, decision: "merge" | "create" | "ignore", targetPk?: string) => void;
}) {
  const { t } = useTranslation();

  if (rows.length === 0) {
    return (
      <EmptyState
        icon={<NavIcon name="duplicate" />}
        title={t("imports.duplicate.empty.title")}
        hint={t("imports.duplicate.empty.hint")}
      />
    );
  }

  return (
    <ul className="imports-dup__list">
      {rows.map((row) => {
        const issue = row.issues.find((i) => i.code === "probable_duplicate" || i.code === "duplicate_in_file");
        const candidates: ImportIssueCandidate[] = issue?.meta?.candidates ?? [];
        const decided = row.decision?.duplicate;
        const busy = busyRows.has(row.row_number);
        return (
          <li key={row.row_number} className="imports-dup__group">
            <div className="imports-dup__file-row">
              <span className="imports-dup__row-num muted">{t("imports.review.rowHeader")} {row.row_number}</span>
              <Bdi>
                <span className="imports-dup__name">{rowLabel(row, nameField)}</span>
              </Bdi>
              {decided && (
                <span className="imports-dup__decided">
                  <NavIcon name="check" />
                  {t(`imports.duplicate.decided.${decided}`)}
                </span>
              )}
            </div>

            {row.group_meta && (
              // Grouped (document) entities: the merge/create/ignore decision below applies to the
              // WHOLE document, not just this line — this line is always the one that carries the
              // document's own natural key (FILE_15 CONFIRMED SCOPE), so a summary here is enough,
              // no separate group-aware layout needed.
              <p className="imports-dup__doc-summary muted">
                {headerFields
                  .filter((name) => name !== "file_total_minor" && row.group_meta?.header[name])
                  .map((name) => String(row.group_meta?.header[name]))
                  .join(" · ")}
                {" — "}
                {t("imports.review.group.lines", { count: row.group_meta.line_count })}
                {row.group_meta.computed_total_minor !== null &&
                  ` · ${formatMinor(row.group_meta.computed_total_minor)}`}
              </p>
            )}

            {candidates.length === 0 ? (
              <p className="imports-dup__note muted">{t("imports.duplicate.inFileOnly")}</p>
            ) : (
              <ul className="imports-dup__candidates">
                {candidates.map((c, i) => (
                  <li key={i} className="imports-dup__candidate">
                    <Bdi>
                      <span>{c.label}</span>
                    </Bdi>
                    <span className="imports-dup__similarity">{t(`imports.duplicate.similarity.${similarityWord(c.score)}`)}</span>
                    {c.pk && !decided && (
                      <button
                        type="button"
                        className="btn btn--ghost"
                        disabled={busy}
                        onClick={() => onDecide(row.row_number, "merge", c.pk)}
                      >
                        {t("imports.duplicate.action.merge")}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {!decided && (
              <div className="imports-dup__actions">
                <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => onDecide(row.row_number, "create")}>
                  {t("imports.duplicate.action.create")}
                </button>
                <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => onDecide(row.row_number, "ignore")}>
                  {t("imports.duplicate.action.ignore")}
                </button>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
