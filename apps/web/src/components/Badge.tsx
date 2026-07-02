import type { ReactNode } from "react";

import "./Badge.css";

// The seven semantic tones a status badge can carry. The first five mirror the
// workflow InstanceStatus set; `accent` marks a billing milestone (invoiced/billed),
// `neutral` is the quiet "closed/draft" rest state.
export type BadgeTone =
  | "pending"
  | "running"
  | "waiting"
  | "completed"
  | "failed"
  | "accent"
  | "neutral";

/**
 * One status chip for the whole app — replaces the per-module `.sales-badge`,
 * `.pur-badge`, `.crm-badge` recipes and the standalone `.pill`. Domain status →
 * tone mapping lives in `lib/statusTone.ts`; the label is the caller's responsibility
 * (already translated). Colour always pairs with the word it sits beside.
 */
export function Badge({ tone = "pending", children }: { tone?: BadgeTone; children: ReactNode }) {
  return <span className={`badge badge--${tone}`} data-tone={tone}>{children}</span>;
}
