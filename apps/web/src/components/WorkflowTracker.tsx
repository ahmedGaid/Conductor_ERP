import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  historyByStage,
  type StageHistoryEntry,
  type WfStep,
  type WorkflowKind,
} from "../lib/workflow";
import { StageSnapshot } from "./StageSnapshot";
import "./workflowTracker.css";

/**
 * WorkflowTracker — always-visible lifecycle strip for a transaction. Shows every
 * stage (Create → Confirm → … → Payment) with the current stage marked, so the user
 * always sees the whole journey and where they are. Return/cancellation appear as an
 * exception step at the end. Colour is the module accent (done/current); the rest is
 * monochrome. Stage labels reuse the kind's i18n (workflow.<kind>.<key>).
 *
 * When `history` is supplied, a stage that has been reached becomes a button: clicking it opens a
 * snapshot of the order exactly as it was at that stage (who, when, and the full record).
 */
export function WorkflowTracker({
  kind,
  steps,
  history,
}: {
  kind: WorkflowKind;
  steps: WfStep[];
  history?: StageHistoryEntry[];
}) {
  const { t } = useTranslation();
  const byStage = history ? historyByStage(history) : {};
  const [openStage, setOpenStage] = useState<string | null>(null);

  const open = openStage && byStage[openStage] ? openStage : null;

  return (
    <div className="wf-wrap">
      <ol className="wf" aria-label={t("workflow.label")}>
        {steps.map((s, i) => {
          const entry = byStage[s.key];
          const marker = (
            <span className="wf__marker">
              {s.state === "done" && !s.exception ? (
                <svg viewBox="0 0 24 24" className="wf__check" aria-hidden="true">
                  <path d="m5 12 5 5 9-10" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : (
                <span aria-hidden="true">{s.exception ? "!" : i + 1}</span>
              )}
            </span>
          );
          const label = <span className="wf__label">{t(`workflow.${kind}.${s.key}`)}</span>;
          const cls = `wf__step wf__step--${s.state}${s.exception ? " wf__step--exception" : ""}`;

          return (
            <li key={s.key} className={cls} aria-current={s.state === "current" ? "step" : undefined}>
              {entry ? (
                <button
                  type="button"
                  className="wf__hit"
                  aria-expanded={open === s.key}
                  onClick={() => setOpenStage((cur) => (cur === s.key ? null : s.key))}
                >
                  {marker}
                  {label}
                </button>
              ) : (
                <>
                  {marker}
                  {label}
                </>
              )}
            </li>
          );
        })}
      </ol>

      {open && (
        <StageSnapshot
          kind={kind}
          stageKey={open}
          entry={byStage[open]}
          onClose={() => setOpenStage(null)}
        />
      )}
    </div>
  );
}
