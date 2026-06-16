import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import "./EmptyState.css";

interface EmptyStateProps {
  /** What this list is / why it's empty (the headline). */
  title: string;
  /** One calm line of guidance. */
  hint?: string;
  /** Optional custom glyph; falls back to a neutral "empty tray" mark. */
  icon?: ReactNode;
  /** Optional primary call-to-action that routes somewhere (e.g. the create screen). */
  action?: { label: string; to: string };
}

const DEFAULT_ICON = (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path d="M3 7l9-4 9 4-9 4-9-4Z" />
    <path d="M3 7v10l9 4 9-4V7" />
    <path d="M12 11v10" />
  </svg>
);

/**
 * A designed empty state: a quiet icon, a headline, an optional line of guidance, and an optional
 * primary action — shown instead of a bare "No data" line, so a fresh install reads as "ready to
 * start", not broken. (Charter: "every empty state is designed — never a bare 'No data.'")
 */
export function EmptyState({ title, hint, icon, action }: EmptyStateProps) {
  return (
    <div className="empty-state card">
      <span className="empty-state__icon" aria-hidden="true">
        {icon ?? DEFAULT_ICON}
      </span>
      <p className="empty-state__title">{title}</p>
      {hint && <p className="empty-state__hint">{hint}</p>}
      {action && (
        <Link className="btn btn--primary empty-state__action" to={action.to}>
          {action.label}
        </Link>
      )}
    </div>
  );
}
