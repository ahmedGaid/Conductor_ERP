import { Component, type ErrorInfo, type ReactNode } from "react";
import { withTranslation, type WithTranslation } from "react-i18next";

import "./AppErrorBoundary.css";

interface Props extends WithTranslation {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

const ICON = (
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
    <circle cx="12" cy="12" r="9" />
    <path d="M12 8v5" />
    <path d="M12 16h.01" />
  </svg>
);

/**
 * Top-level render-error catch: without it, an uncaught error white-screens the whole app.
 * Class component because getDerivedStateFromError/componentDidCatch have no hook equivalent.
 */
class AppErrorBoundaryBase extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("AppErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    const { t } = this.props;
    return (
      <div className="app-error-boundary">
        <span className="app-error-boundary__icon">{ICON}</span>
        <p className="app-error-boundary__title">{t("errorBoundary.title")}</p>
        <p className="app-error-boundary__hint">{t("errorBoundary.hint")}</p>
        <button
          type="button"
          className="btn btn--primary app-error-boundary__action"
          onClick={() => window.location.reload()}
        >
          {t("errorBoundary.reload")}
        </button>
      </div>
    );
  }
}

export const AppErrorBoundary = withTranslation()(AppErrorBoundaryBase);
