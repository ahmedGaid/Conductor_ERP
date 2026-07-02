import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { NavIcon } from "./icons";
import type { ActionReceipt, FeedbackVariant, ReceiptAction, ReceiptLink } from "./ActionFeedbackContext";
import type { FeedbackMode } from "../lib/feedbackMode";
import "./ActionReceiptCard.css";

// The header glyph carries the variant — colour paired with an icon, meaning "done / attention".
const VARIANT_ICON: Record<FeedbackVariant, string> = {
  success: "checkCircle",
  error: "info",
  info: "info",
};

/**
 * ActionReceiptCard — the after-action panel. Two depths:
 *  - "simple" (default): result + any record it produced (number + link) + the recommended next.
 *  - "rich": adds the business context, facts, warnings, insights, quick actions, related links.
 *
 * Surface-agnostic and monochrome; colour only where it means something (success check, warning),
 * one quiet accent on the recommended next step. Every section is optional.
 */
export function ActionReceiptCard({
  receipt,
  detail,
  onDismiss,
  onPause,
  onResume,
}: {
  receipt: ActionReceipt;
  detail: FeedbackMode;
  onDismiss: () => void;
  onPause?: () => void;
  onResume?: () => void;
}) {
  const { t } = useTranslation();
  const rich = detail === "rich";

  // A receipt action runs, then dismisses the card so it never lingers after the user moves on.
  const fire = (action: ReceiptAction) => () => {
    action.run();
    onDismiss();
  };

  const docLinks = (links: ReceiptLink[], label: string) => (
    <nav className="arc__docs" aria-label={label}>
      {links.map((r) => (
        <Link key={r.to} to={r.to} className="arc__doc-link" onClick={onDismiss}>
          {r.label}
        </Link>
      ))}
    </nav>
  );

  return (
    <div
      className={`arc arc--${receipt.variant}`}
      role="status"
      aria-live="polite"
      onMouseEnter={onPause}
      onMouseLeave={onResume}
      onFocus={onPause}
      onBlur={onResume}
    >
      <div className="arc__head">
        <span className="arc__glyph" aria-hidden="true">
          <NavIcon name={VARIANT_ICON[receipt.variant]} />
        </span>
        <div className="arc__headtext">
          <p className="arc__title">{receipt.title}</p>
          {/* The reason always shows on an error (even in simple mode — it's how you'll fix it). */}
          {(rich || receipt.variant === "error") && receipt.context && <p className="arc__context">{receipt.context}</p>}
        </div>
        <button
          type="button"
          className="arc__close"
          aria-label={t("toast.dismiss")}
          onClick={onDismiss}
        >
          <span aria-hidden="true">×</span>
        </button>
      </div>

      {/* Produced records — the numbers worth a one-click open. Shown in both modes. */}
      {receipt.documents && receipt.documents.length > 0 && docLinks(receipt.documents, t("feedback.documentsLabel"))}

      {/* The way out of a blocker — fix links on an error receipt. Shown in both modes. */}
      {receipt.resolutions && receipt.resolutions.length > 0 && docLinks(receipt.resolutions, t("feedback.resolutionsLabel"))}

      {rich && receipt.facts && receipt.facts.length > 0 && (
        <dl className="arc__facts">
          {receipt.facts.map((f) => (
            <div key={f.label} className="arc__fact">
              <dt className="arc__fact-label">{f.label}</dt>
              <dd className="arc__fact-value">{f.value}</dd>
            </div>
          ))}
        </dl>
      )}

      {rich && receipt.warnings && receipt.warnings.length > 0 && (
        <ul className="arc__warnings">
          {receipt.warnings.map((w) => (
            <li key={w} className="arc__warning">
              <span className="arc__warning-icon" aria-hidden="true">
                <NavIcon name="flag" />
              </span>
              <span>{w}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Recommended next — shown in both modes; quick actions are rich only. */}
      {(receipt.next || (rich && receipt.quickActions && receipt.quickActions.length > 0)) && (
        <div className="arc__actions">
          {receipt.next && (
            <button type="button" className="btn btn--primary btn--sm" onClick={fire(receipt.next)}>
              {receipt.next.icon && <NavIcon name={receipt.next.icon} />}
              {receipt.next.label}
            </button>
          )}
          {rich &&
            receipt.quickActions?.map((a) => (
              <button key={a.label} type="button" className="btn btn--sm" onClick={fire(a)}>
                {a.icon && <NavIcon name={a.icon} />}
                {a.label}
              </button>
            ))}
        </div>
      )}

      {rich && receipt.related && receipt.related.length > 0 && (
        <nav className="arc__related" aria-label={t("feedback.relatedLabel")}>
          {receipt.related.map((r) => (
            <Link key={r.to} to={r.to} className="arc__related-link" onClick={onDismiss}>
              {r.label}
            </Link>
          ))}
        </nav>
      )}

      {rich && receipt.insights && receipt.insights.length > 0 && (
        <ul className="arc__insights">
          {receipt.insights.map((ins) => (
            <li key={ins} className="arc__insight">
              <span className="arc__insight-icon" aria-hidden="true">
                <NavIcon name="star" />
              </span>
              <span>{ins}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
