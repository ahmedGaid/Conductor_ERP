import type { ReactNode } from "react";
import "./moduleHeader.css";

/**
 * ModuleHeader — document title row for a transaction detail/create page.
 *
 * A thin module-colour bar (the inherited --module-bar token, set per module on the
 * shell) sits beside the document number; the page's own status badge is the only
 * other colour. The breadcrumb above the page is rendered centrally by RouteBreadcrumb.
 */
export interface ModuleHeaderProps {
  /** The document number/title (rendered in the Latin face). */
  title: string;
  /** The page's own status badge — the one place page colour is allowed. */
  status?: ReactNode;
  /** Optional sub-line under the title (party · warehouse · date, etc.). */
  subtitle?: ReactNode;
}

export function ModuleHeader({ title, status, subtitle }: ModuleHeaderProps) {
  return (
    <div className="modhead">
      <div className="modhead__row">
        <span className="modhead__bar" aria-hidden="true" />
        <h2 className="latin modhead__title">{title}</h2>
        {status != null && <span className="modhead__status">{status}</span>}
      </div>
      {subtitle != null && <p className="muted modhead__subtitle">{subtitle}</p>}
    </div>
  );
}
