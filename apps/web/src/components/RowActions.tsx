import { type ReactNode } from "react";

import "./RowActions.css";

interface RowActionsProps {
  children: ReactNode;
  /** Accessible group name for the cluster of buttons. */
  label: string;
  /** Extra layout classes to merge (e.g. an existing per-module action container). */
  className?: string;
}

/**
 * A trailing cluster of per-row quick actions that stays visually quiet until its row is hovered
 * or holds keyboard focus — the calm, low-noise alternative to showing a button on every row at
 * full strength. The reveal is pure CSS keyed off `tr:hover` / `tr:focus-within` (see RowActions.css),
 * so it needs no JS and works for keyboard users; on touch devices (no hover) the actions are always
 * shown. The buttons stay in the DOM and in the tab order the whole time, so nothing is hidden from
 * assistive tech — only the opacity changes.
 */
export function RowActions({ children, label, className }: RowActionsProps) {
  return (
    <div className={className ? `row-actions ${className}` : "row-actions"} role="group" aria-label={label}>
      {children}
    </div>
  );
}
