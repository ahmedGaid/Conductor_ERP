import type { CSSProperties, ReactNode } from "react";

import { useModuleIdentity, type DocumentModule } from "../hooks/useModuleIdentity";
import "./documentDetail.css";

export interface DocumentSummaryItem {
  label: ReactNode;
  /** Pre-formatted value node (already wrapped in <Bdi> / formatted by lib/money by the caller). */
  value: ReactNode;
  /** The one figure that matters most for the document's current state — rendered larger, and tinted
   *  in the module hue under the "accent" identity mode. Exactly one item should set this. */
  hero?: boolean;
}

/**
 * The KPI strip above a document's line table. One shared shape for every detail page (sales order,
 * quotation, purchase order, request) so the figures read identically everywhere. The `hero` item is
 * the single figure that matters now (outstanding on a billed order, total on a quotation); it reads
 * larger than the rest, and picks up the module hue only in the "accent" module-identity mode.
 */
export function DocumentSummary({
  module,
  items,
}: {
  module?: DocumentModule;
  items: DocumentSummaryItem[];
}) {
  const [mode] = useModuleIdentity();
  const identity = module ? mode : "mono";
  const style =
    module && identity === "accent"
      ? ({ ["--doc-module" as string]: `var(--color-module-${module}-strong)` } as CSSProperties)
      : undefined;

  return (
    <div className="docsummary" data-identity={identity} data-module={module} style={style}>
      {items.map((item, i) => (
        <div key={i} className={`docsummary__item${item.hero ? " docsummary__item--hero" : ""}`}>
          <span className="docsummary__label">{item.label}</span>
          <span className="docsummary__value">{item.value}</span>
        </div>
      ))}
    </div>
  );
}
