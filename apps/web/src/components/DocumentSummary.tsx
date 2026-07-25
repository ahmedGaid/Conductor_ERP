import type { ReactNode } from "react";

import "./documentDetail.css";

export interface DocumentSummaryItem {
  label: ReactNode;
  /** Pre-formatted value node (already wrapped in <Bdi> / formatted by lib/money by the caller). */
  value: ReactNode;
  /** The one figure that matters most for the document's current state — rendered larger. Exactly
   *  one item should set this. */
  hero?: boolean;
}

/**
 * The KPI strip above a document's line table. One shared shape for every detail page (sales order,
 * quotation, purchase order, request) so the figures read identically everywhere. The `hero` item is
 * the single figure that matters now (outstanding on a billed order, total on a quotation); it reads
 * larger than the rest. Monochrome — hierarchy by size/weight, never colour.
 */
export function DocumentSummary({ items }: { items: DocumentSummaryItem[] }) {
  return (
    <div className="docsummary">
      {items.map((item, i) => (
        <div key={i} className={`docsummary__item${item.hero ? " docsummary__item--hero" : ""}`}>
          <span className="docsummary__label">{item.label}</span>
          <span className="docsummary__value">{item.value}</span>
        </div>
      ))}
    </div>
  );
}
