import { useTranslation } from "react-i18next";

import { NavIcon } from "../app/icons";
import { Bdi } from "./Bdi";
import { Tooltip } from "./Tooltip";
import "./metaCells.css";

// A money doc is "due soon" inside this window, "overdue" once past it. Three days is the collections
// signal Egyptian SMBs act on (decision 7, FILE_00).
const DUE_SOON_DAYS = 3;

/** Whole days from today (local midnight) to the due date; negative once the date has passed. */
function daysUntil(due: Date): number {
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const startOfDue = new Date(due);
  startOfDue.setHours(0, 0, 0, 0);
  return Math.round((startOfDue.getTime() - startOfToday.getTime()) / 86_400_000);
}

/**
 * Due-date cell with a collections signal. A settled (paid) doc, or one with no due date, shows the
 * plain date. An open doc turns warn ("يستحق قريبًا") as the date nears and danger ("متأخر", with a
 * days count) once it passes — colour always paired with its word (brand rule).
 *
 * Digits stay Latin in BOTH locales: the date is formatted through the `-nu-latn` numbering
 * extension (Arabic month names, Latin figures) and the overdue count is a raw number in a `.num`
 * `<Bdi>`.
 */
export function DueMarker({ dueDate, settled = false }: { dueDate: string | null; settled?: boolean }) {
  const { t, i18n } = useTranslation();

  if (!dueDate) return <span className="meta-due meta-due--none">—</span>;

  const due = new Date(dueDate);
  const dateStr = new Intl.DateTimeFormat(`${i18n.language}-u-nu-latn`, { dateStyle: "medium" }).format(due);
  const dateNode = (
    <Bdi>
      <span className="num">{dateStr}</span>
    </Bdi>
  );

  if (settled) return <span className="meta-due">{dateNode}</span>;

  const days = daysUntil(due);

  if (days < 0) {
    const late = Math.abs(days);
    return (
      <Tooltip label={t("due.overdueBy", { count: late })}>
        <span className="meta-due meta-due--overdue">
          <NavIcon name="clock" />
          <span>{t("due.overdue")}</span>
          <Bdi>
            <span className="num">{late}</span>
          </Bdi>
        </span>
      </Tooltip>
    );
  }

  if (days <= DUE_SOON_DAYS) {
    return (
      <span className="meta-due meta-due--soon">
        <span>{t("due.soon")}</span>
        {dateNode}
      </span>
    );
  }

  return <span className="meta-due">{dateNode}</span>;
}
