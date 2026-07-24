import { useTranslation } from "react-i18next";

import { relativeTime } from "../lib/relativeTime";
import "./DraftRecoveryBanner.css";

interface Props {
  /** Human label for what's being recovered, e.g. the translated "customer". */
  entityLabel: string;
  /** ISO timestamp of the draft's last activity. */
  lastActiveAt: string;
  onContinue: () => void;
  onDiscard: () => void;
}

/**
 * Calm "Continue where you left off?" surface shown when an unfinished draft is detected on entry.
 * No colour in the frame (monochrome chrome); the one primary button carries the recommended action.
 */
export function DraftRecoveryBanner({ entityLabel, lastActiveAt, onContinue, onDiscard }: Props) {
  const { t, i18n } = useTranslation();
  return (
    <div className="draft-recovery" role="status">
      <div className="draft-recovery__text">
        <p className="draft-recovery__title">{t("drafts.recovery.title")}</p>
        <p className="draft-recovery__hint">
          {t("drafts.recovery.hint", { entity: entityLabel, when: relativeTime(lastActiveAt, i18n.language) })}
        </p>
      </div>
      <div className="draft-recovery__actions">
        <button type="button" className="btn btn--primary btn--sm" onClick={onContinue}>
          {t("drafts.recovery.continue")}
        </button>
        <button type="button" className="btn btn--sm btn--ghost" onClick={onDiscard}>
          {t("drafts.recovery.discard")}
        </button>
      </div>
    </div>
  );
}
