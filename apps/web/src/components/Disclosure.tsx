import { type ReactNode } from "react";

import "./Disclosure.css";

/**
 * Progressive disclosure: a labelled section that's collapsed by default so a busy detail screen
 * leads with what matters and tucks secondary information one click away. Built on native
 * <details>/<summary> — keyboard-accessible and works with no JS state. Direction-agnostic (the
 * chevron is vertical, so it reads the same in RTL and LTR).
 */
export function Disclosure({
  summary,
  children,
  defaultOpen = false,
}: {
  summary: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details className="disclosure" open={defaultOpen}>
      <summary className="disclosure__summary">
        <svg
          className="disclosure__chevron"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.8}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
        <span>{summary}</span>
      </summary>
      <div className="disclosure__body">{children}</div>
    </details>
  );
}
