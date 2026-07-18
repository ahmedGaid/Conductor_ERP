import { useState } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../app/icons";
import { dismissMilestone, getPendingMilestone, type Milestone } from "../api/milestones";
import { useAsync } from "../hooks/useAsync";

// Calm milestone moments (arp-roadmap track P item 2) — a quiet, dismissible acknowledgment when
// the company crosses a real milestone (first profitable month, a round invoice count). No
// confetti, no sound — that would break the quiet/calm brand. Dismissal is company-wide (the
// backend acks it for everyone), so this never nags again once anyone's seen it.
export function MilestoneBanner() {
  const { t } = useTranslation();
  const { data } = useAsync(
    () => getPendingMilestone().then((r) => r.milestone),
    [],
    "milestone",
  );
  const [dismissedKey, setDismissedKey] = useState<string | null>(null);

  if (!data || data.key === dismissedKey) return null;

  const milestone: Milestone = data;

  function dismiss() {
    setDismissedKey(milestone.key);
    dismissMilestone(milestone.key).catch(() => {
      // best-effort — if the request fails, it simply reappears next visit, not lost data
    });
  }

  return (
    <div className="card dash__panel dash__milestone">
      <span className="dash__milestone-icon" aria-hidden="true">
        <NavIcon name="trendUp" />
      </span>
      <p className="dash__milestone-text">
        {milestone.kind === "invoice_count"
          ? t("dashboard.milestone.invoiceCount", { count: milestone.value ?? 0 })
          : t("dashboard.milestone.firstProfitableMonth")}
      </p>
      <button className="dash__milestone-dismiss" type="button" onClick={dismiss}>
        {t("dashboard.milestone.dismiss")}
      </button>
    </div>
  );
}
