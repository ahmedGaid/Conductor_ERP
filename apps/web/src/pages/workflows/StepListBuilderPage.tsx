import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useToast } from "../../app/ToastContext";
import { createWorkflow } from "../../api/workflows";
import { stepsToGraph, type Step } from "../../lib/stepList";
import { ApprovalStepForm } from "./steps/ApprovalStepForm";
import { ConditionStepForm } from "./steps/ConditionStepForm";
import { NotificationStepForm } from "./steps/NotificationStepForm";
import "./StepListBuilderPage.css";

// v1 scope: notification/approval/condition have real config forms. assistant_action and
// api_call stay canvas/Advanced-only — their config forms mean reusing NodeConfigPanel's
// internals in a new context, which is separately-planned work, not a two-line addition here.
const STEP_TYPES = ["notification", "approval", "condition"] as const;

export function StepListBuilderPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [saving, setSaving] = useState(false);
  const hasBranch = steps.some((s) => s.branch);

  function addStep(type: Step["type"]) {
    setSteps((s) => [...s, { key: `step_${s.length}`, type, config: {} }]);
  }

  function updateStep(index: number, config: Record<string, unknown>) {
    setSteps((s) => s.map((step, i) => (i === index ? { ...step, config } : step)));
  }

  async function onSave() {
    setSaving(true);
    try {
      const { nodes, edges } = stepsToGraph(steps);
      const wf = await createWorkflow({ name, nodes, edges });
      toast.show(t("automations.saved"), "success");
      navigate(`/workflows/${wf.id}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setSaving(false);
    }
  }

  function stepTypeLabel(type: Step["type"]) {
    const key = type === "assistant_action" ? "assistant" : type === "api_call" ? "apiCall" : type;
    return t(`automations.steps.type.${key}`);
  }

  return (
    <section className="automations steplist">
      <h1>{t("automations.startFromScratch")}</h1>
      <label className="field">
        <span>{t("automations.title")}</span>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>

      <ol className="steplist__steps">
        {steps.map((step, i) => (
          <li className="steplist__step" key={step.key}>
            <span className="steplist__label">{t("automations.steps.do")}</span>
            <strong>{stepTypeLabel(step.type)}</strong>
            {step.type === "approval" && (
              <ApprovalStepForm config={step.config} onChange={(c) => updateStep(i, c)} />
            )}
            {step.type === "notification" && (
              <NotificationStepForm config={step.config} onChange={(c) => updateStep(i, c)} />
            )}
            {step.type === "condition" && (
              <ConditionStepForm config={step.config} onChange={(c) => updateStep(i, c)} />
            )}
          </li>
        ))}
      </ol>

      <div className="steplist__add">
        {STEP_TYPES.map((type) => (
          <button
            key={type}
            type="button"
            className="btn btn--sm"
            disabled={type === "condition" && hasBranch}
            onClick={() => addStep(type)}
          >
            + {stepTypeLabel(type)}
          </button>
        ))}
      </div>

      <button className="btn btn--primary" onClick={onSave} disabled={saving || !name || steps.length === 0}>
        {t("automations.save")}
      </button>
    </section>
  );
}
