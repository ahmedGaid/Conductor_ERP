import { useTranslation } from "react-i18next";

import { useToastState } from "./ToastContext";
import "./Toaster.css";

/**
 * Renders the live toast stack in a fixed, RTL-aware corner region. Mounted once in the
 * app shell; all firing goes through `useToast()`. `aria-live="polite"` announces new
 * toasts to assistive tech without stealing focus.
 */
export function Toaster() {
  const { t } = useTranslation();
  const { toasts, dismiss } = useToastState();

  if (toasts.length === 0) return null;

  return (
    <div className="toaster" role="region" aria-label={t("toast.region")} aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast--${toast.variant}`} role="status">
          <span className="toast__dot" aria-hidden="true" />
          <span className="toast__msg">{toast.message}</span>
          {toast.action && (
            <button
              type="button"
              className="toast__action"
              onClick={() => {
                toast.action!.onClick();
                dismiss(toast.id);
              }}
            >
              {toast.action.label}
            </button>
          )}
          <button
            type="button"
            className="toast__close"
            aria-label={t("toast.dismiss")}
            onClick={() => dismiss(toast.id)}
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>
      ))}
    </div>
  );
}
