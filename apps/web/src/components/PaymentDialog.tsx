import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { formatMinor, minorToAmount, parseToMinor } from "../lib/money";
import "./confirmDialog.css";
import "./paymentDialog.css";

/**
 * Amount-entry dialog for collecting a sales payment / recording a purchasing payment. Defaults
 * to the full outstanding balance (one-click flow unchanged) but is editable for a partial
 * collection — Egyptian SMBs run on partial cash collections, not just full settlement.
 */
export function PaymentDialog({
  open,
  title,
  outstandingMinor,
  currency,
  confirmLabel,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  outstandingMinor: number;
  currency: string;
  confirmLabel: string;
  onConfirm: (amountMinor: number) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDialogElement>(null);
  const [amount, setAmount] = useState("");

  useEffect(() => {
    const dlg = ref.current;
    if (!dlg) return;
    if (open && !dlg.open) {
      setAmount(minorToAmount(outstandingMinor));
      dlg.showModal();
    } else if (!open && dlg.open) {
      dlg.close();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function onBackdropClick(e: React.MouseEvent) {
    if (e.target === ref.current) onClose();
  }

  const parsed = parseToMinor(amount);
  const error =
    parsed === null || parsed <= 0
      ? t("document.paymentDialog.errorZero")
      : parsed > outstandingMinor
        ? t("document.paymentDialog.errorExceeds")
        : null;
  const remaining = parsed !== null ? Math.max(outstandingMinor - parsed, 0) : outstandingMinor;

  function confirm() {
    if (error || parsed === null) return;
    onClose();
    onConfirm(parsed);
  }

  return (
    <dialog ref={ref} className="confirm" aria-label={title} onClose={onClose} onCancel={onClose} onClick={onBackdropClick}>
      <div className="confirm__panel">
        <h2 className="confirm__title">{title}</h2>

        <dl className="payment-dialog__summary">
          <div className="payment-dialog__row">
            <dt>{t("document.paymentDialog.outstandingNow")}</dt>
            <dd className="latin">{formatMinor(outstandingMinor, currency)}</dd>
          </div>
          <div className="payment-dialog__row">
            <dt>{t("document.paymentDialog.willRemain")}</dt>
            <dd className="latin">{formatMinor(remaining, currency)}</dd>
          </div>
        </dl>

        <label className="payment-dialog__field">
          <span>{t("document.paymentDialog.amount")}</span>
          <input
            className="latin"
            inputMode="decimal"
            autoFocus
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") confirm();
            }}
          />
        </label>
        {error && <p className="error-text">{error}</p>}

        <div className="confirm__actions">
          <button type="button" className="btn" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button type="button" className="btn btn--primary" disabled={!!error} onClick={confirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}
