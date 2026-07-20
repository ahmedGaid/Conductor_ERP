import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { type RelatedType } from "../api/crm";
import { ActivityFeed } from "./ActivityFeed";
import "../app/CommandPalette.css";
import "./activityDialog.css";

/**
 * Hosts an `ActivityFeed` for one record in a modal, for the CRM queues that have no detail page
 * of their own (leads, tickets) — opening a whole route for "who called this lead?" would be a
 * heavier answer than the question. Same native `<dialog>` shell as the command palette and the
 * import dialog: top layer, focus trap and Esc for free.
 */
export function ActivityDialog({
  open,
  onClose,
  relatedType,
  relatedRef,
  recordLabel,
}: {
  open: boolean;
  onClose: () => void;
  relatedType: RelatedType;
  relatedRef: string;
  /** What the user sees as the record's name in the title (lead name, ticket subject). */
  recordLabel: string;
}) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dlg = ref.current;
    if (!dlg) return;
    if (open && !dlg.open) dlg.showModal();
    else if (!open && dlg.open) dlg.close();
  }, [open]);

  const title = t("crm.activity.dialogTitle", { record: recordLabel });

  return (
    <dialog
      ref={ref}
      className="cmdp"
      aria-label={title}
      onClose={onClose}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="cmdp__panel activity-dialog">
        <header className="activity-dialog__head">
          <h2 className="activity-dialog__title">{title}</h2>
          <button type="button" className="btn btn--ghost btn--sm" onClick={onClose}>
            {t("common.close")}
          </button>
        </header>
        <div className="activity-dialog__body">
          {/* Remounted per record: the feed keys its own fetch off these props. */}
          {open && <ActivityFeed relatedType={relatedType} relatedRef={relatedRef} />}
        </div>
      </div>
    </dialog>
  );
}
