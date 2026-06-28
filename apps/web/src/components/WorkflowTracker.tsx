import { useTranslation } from "react-i18next";

import type { WfStep, WorkflowKind } from "../lib/workflow";
import "./workflowTracker.css";

/**
 * WorkflowTracker — always-visible lifecycle strip for a transaction. Shows every
 * stage (Create → Confirm → … → Payment) with the current stage marked, so the user
 * always sees the whole journey and where they are. Return/cancellation appear as an
 * exception step at the end. Colour is the module accent (done/current); the rest is
 * monochrome. Stage labels reuse the kind's i18n (workflow.<kind>.<key>).
 */
export function WorkflowTracker({ kind, steps }: { kind: WorkflowKind; steps: WfStep[] }) {
  const { t } = useTranslation();

  return (
    <ol className="wf" aria-label={t("workflow.label")}>
      {steps.map((s, i) => (
        <li
          key={s.key}
          className={`wf__step wf__step--${s.state}${s.exception ? " wf__step--exception" : ""}`}
          aria-current={s.state === "current" ? "step" : undefined}
        >
          <span className="wf__marker">
            {s.state === "done" && !s.exception ? (
              <svg viewBox="0 0 24 24" className="wf__check" aria-hidden="true">
                <path d="m5 12 5 5 9-10" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              <span aria-hidden="true">{s.exception ? "!" : i + 1}</span>
            )}
          </span>
          <span className="wf__label">{t(`workflow.${kind}.${s.key}`)}</span>
        </li>
      ))}
    </ol>
  );
}
