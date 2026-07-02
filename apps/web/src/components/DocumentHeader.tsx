import type { ReactNode } from "react";

import { NavIcon } from "../app/icons";
import { DocumentMenu, type DocMenuItem } from "./DocumentMenu";
import "./documentDetail.css";

/**
 * The header row of a transaction detail page: document number + status badge on one side, the
 * primary lifecycle action and the ⋯ overflow menu on the other. Monochrome chrome — the status
 * badge is the only colour, plus the accent on the primary button. Shared by every order /
 * quotation / request detail page so they read as one family.
 */
export function DocumentHeader({
  number,
  status,
  primary,
  menu,
  menuLabel,
}: {
  number: string;
  status?: ReactNode;
  primary?: { label: string; icon?: string; onClick: () => void; disabled?: boolean } | null;
  menu: DocMenuItem[];
  menuLabel: string;
}) {
  return (
    <header className="docdetail__head">
      <div className="docdetail__heading">
        <h1 className="docdetail__number latin">{number}</h1>
        {status != null && <span className="docdetail__status">{status}</span>}
      </div>
      <div className="docdetail__actions">
        {primary && (
          <button type="button" className="btn btn--primary" disabled={primary.disabled} onClick={primary.onClick}>
            {primary.icon && <NavIcon name={primary.icon} />}
            <span>{primary.label}</span>
          </button>
        )}
        <DocumentMenu items={menu} ariaLabel={menuLabel} />
      </div>
    </header>
  );
}
