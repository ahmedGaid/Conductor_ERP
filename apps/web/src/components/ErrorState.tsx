import { useTranslation } from "react-i18next";

import "./ErrorState.css";

interface ErrorStateProps {
  /** The raw failure message — shown muted, below the calm headline. */
  message?: string | null;
  /** Wire to the loader's `reload` so the user can try again in place. */
  onRetry?: () => void;
}

const ALERT_ICON = (
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
    <path d="M10.3 3.8 2.4 17.3a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.8a2 2 0 0 0-3.4 0Z" />
    <path d="M12 9v4" />
    <path d="M12 17h.01" />
  </svg>
);

/**
 * A designed error state for a failed data load: a quiet alert mark, a calm blame-free headline,
 * the raw message kept muted underneath (so it's still diagnosable), and a single "Retry" action
 * wired to the loader's reload — shown instead of a bare red line, so a failed fetch reads as
 * "try again", not "broken". (Charter: "every error state is designed — never a bare line.")
 */
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  const { t } = useTranslation();
  return (
    <div className="error-state card" role="alert">
      <span className="error-state__icon" aria-hidden="true">
        {ALERT_ICON}
      </span>
      <p className="error-state__title">{t("common.error.title")}</p>
      <p className="error-state__hint">{t("common.error.hint")}</p>
      {message && <p className="error-state__detail">{message}</p>}
      {onRetry && (
        <button type="button" className="btn btn--primary error-state__action" onClick={onRetry}>
          {t("common.retry")}
        </button>
      )}
    </div>
  );
}
