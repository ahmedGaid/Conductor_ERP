import { useTranslation } from "react-i18next";

import "./DraftStatusIndicator.css";

interface Props {
  status: "idle" | "saving" | "saved";
  savedAt: Date | null;
}

/** Subtle inline "Saving… / Changes saved" text. Renders nothing until the first save begins. */
export function DraftStatusIndicator({ status, savedAt }: Props) {
  const { t } = useTranslation();
  if (status === "idle" && !savedAt) return null;
  const label = status === "saving" ? t("drafts.status.saving") : t("drafts.status.saved");
  return (
    <span className="draft-status" data-state={status} aria-live="polite">
      {label}
    </span>
  );
}
