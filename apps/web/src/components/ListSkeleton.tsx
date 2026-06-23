import { useTranslation } from "react-i18next";

interface ListSkeletonProps {
  /** Body placeholder rows to render under the title bar. */
  rows?: number;
  /** Render the leading title bar (omit when the page already shows its heading). */
  title?: boolean;
}

/**
 * The one designed loading state for a cold list/table load: a title bar plus a few
 * layout-shaped rows that shimmer, so a page paints structure instead of a blank
 * "Loading…" beat. Centralises what used to be an inline skeleton blob copied across
 * every page, so the load reads the same calm way everywhere. (Charter: "every loading
 * state is designed.") Shimmer flattens to a static block under reduced-motion.
 */
export function ListSkeleton({ rows = 4, title = true }: ListSkeletonProps) {
  const { t } = useTranslation();
  return (
    <div className="page-skeleton" aria-busy="true">
      <span className="visually-hidden">{t("common.loading")}</span>
      {title && <span className="skeleton skeleton--title" />}
      {Array.from({ length: rows }, (_, i) => (
        <span key={i} className="skeleton skeleton--row" />
      ))}
    </div>
  );
}
