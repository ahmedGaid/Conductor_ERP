import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import "./confirmDialog.css";

/**
 * A small confirmation modal for a destructive or irreversible action (e.g. Cancel Order). Native
 * <dialog> so it gets the top layer, focus trap and Esc for free — the same shell as the command
 * palette. Monochrome; colour only on the danger confirm button. RTL-safe via logical properties.
 */
export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  cancelLabel,
  danger = false,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  body?: string;
  confirmLabel: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dlg = ref.current;
    if (!dlg) return;
    if (open && !dlg.open) dlg.showModal();
    else if (!open && dlg.open) dlg.close();
  }, [open]);

  function onBackdropClick(e: React.MouseEvent) {
    if (e.target === ref.current) onClose();
  }

  return (
    <dialog ref={ref} className="confirm" aria-label={title} onClose={onClose} onCancel={onClose} onClick={onBackdropClick}>
      <div className="confirm__panel">
        <h2 className="confirm__title">{title}</h2>
        {body && <p className="confirm__body">{body}</p>}
        <div className="confirm__actions">
          <button type="button" className="btn" onClick={onClose}>
            {cancelLabel ?? t("common.cancel")}
          </button>
          <button
            type="button"
            className={danger ? "btn btn--danger" : "btn btn--primary"}
            onClick={() => {
              onClose();
              onConfirm();
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}
