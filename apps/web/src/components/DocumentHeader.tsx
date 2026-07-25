import type { ReactNode } from "react";

import { NavIcon } from "../app/icons";
import { useModuleIdentity, type DocumentModule } from "../hooks/useModuleIdentity";
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
 *
 * `module` + `moduleLabel` carry the optional module-identity cue (sales/purchasing) rendered per the
 * current preview mode (see useModuleIdentity): "mono" shows nothing extra, "accent" tints the number
 * rule in the module hue, "tag" shows a small coloured module chip. The hue always pairs with the
 * module word so it reads as wayfinding, never decoration.
 */
export function DocumentHeader({
  number,
  status,
  module,
  moduleLabel,
  actions,
}: {
  number: string;
  status?: ReactNode;
  module?: DocumentModule;
  moduleLabel?: string;
  actions?: ReactNode;
}) {
  const [mode] = useModuleIdentity();
  const identity = module ? mode : "mono";
  const moduleStyle =
    module && identity !== "mono"
      ? ({
          ["--doc-module" as string]: `var(--color-module-${module})`,
          ["--doc-module-strong" as string]: `var(--color-module-${module}-strong)`,
          ["--doc-module-subtle" as string]: `var(--color-module-${module}-subtle)`,
        } as React.CSSProperties)
      : undefined;

  return (
    <header className="docdetail__head" data-identity={identity} data-module={module} style={moduleStyle}>
      <div className="docdetail__heading">
        {identity === "tag" && moduleLabel && (
          <span className="docdetail__module-tag">
            <span className="docdetail__module-dot" aria-hidden="true" />
            {moduleLabel}
          </span>
        )}
        <h1 className="docdetail__number latin">{number}</h1>
        {status != null && <span className="docdetail__status">{status}</span>}
      </div>
      {actions != null && <div className="docdetail__actions">{actions}</div>}
    </header>
  );
}
