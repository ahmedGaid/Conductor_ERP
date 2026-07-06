import type { ReactNode } from "react";

import { NavIcon } from "../app/icons";
import "./documentDetail.css";

/** The one visible primary action a detail page publishes into the page header bar. */
export interface DocumentPrimary {
  label: string;
  icon?: string;
  onClick: () => void;
  disabled?: boolean;
}

/**
 * Renders a page's primary action for the PageHeaderBar slot (via useSetPageActions). One shared
 * shape so every detail page's primary reads identically in the bar.
 */
export function DocumentPrimaryButton({ action }: { action: DocumentPrimary }) {
  return (
    <button type="button" className="btn btn--primary" disabled={action.disabled} onClick={action.onClick}>
      {action.icon && <NavIcon name={action.icon} />}
      <span>{action.label}</span>
    </button>
  );
}

/**
 * The heading row of a transaction detail page: document number + status badge. Monochrome chrome —
 * the status badge is the only colour. The page's primary action and ⋯ menu live in the sticky
 * PageHeaderBar (published via useSetPageActions), so every detail page reads as one family.
 */
export function DocumentHeader({
  number,
  status,
}: {
  number: string;
  status?: ReactNode;
}) {
  return (
    <header className="docdetail__head">
      <div className="docdetail__heading">
        <h1 className="docdetail__number latin">{number}</h1>
        {status != null && <span className="docdetail__status">{status}</span>}
      </div>
    </header>
  );
}
