import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { NavIcon } from "../app/icons";
import "./BulkActionBar.css";

/**
 * Floating bar that appears when one or more rows are selected (see useRowSelection). Mirrors
 * Linear's selection bar: a count, the contextual actions for the selection, and a clear control.
 * Monochrome — it's brand near-black, not an accent; selection is chrome. Actions are passed as
 * children so each list supplies the verbs that make sense for its rows.
 */
export function BulkActionBar({
  count,
  onClear,
  children,
}: {
  count: number;
  onClear: () => void;
  children?: ReactNode;
}) {
  const { t } = useTranslation();
  if (count === 0) return null;
  return (
    <div className="bulkbar" role="region" aria-label={t("bulk.region")}>
      <span className="bulkbar__count">
        {t(count === 1 ? "bulk.selectedOne" : "bulk.selected", { count })}
      </span>
      <div className="bulkbar__actions">{children}</div>
      <button type="button" className="bulkbar__clear" onClick={onClear} aria-label={t("bulk.clear")}>
        <NavIcon name="close" />
      </button>
    </div>
  );
}
