import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { BackLink } from "../components/BackLink";

import { decideInstance, getInstance } from "../api/workflows";
import type { InstanceDetail, NodeRun } from "../api/types";
import { useAsync } from "../hooks/useAsync";
import { ErrorState } from "../components/ErrorState";
import { useToast } from "../app/ToastContext";
import { runOptimistic } from "../lib/optimistic";
import { StatusPill } from "../components/StatusPill";
import { Bdi } from "../components/Bdi";
import { ListSkeleton } from "../components/ListSkeleton";
import "./ExecutionViewerPage.css";

export function ExecutionViewerPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload, mutate } = useAsync<InstanceDetail>(
    () => getInstance(id as string),
    [id],
  );
  const [comment, setComment] = useState("");

  // Optimistic decision: leave "waiting" instantly (approve resumes → running, reject fails it) so the
  // decision card dismisses, then settle with the server's instance — it carries the true final status
  // and the new node runs. A failure rolls back to "waiting" and toasts.
  function decide(decision: "approve" | "reject") {
    if (!id || !data) return;
    void runOptimistic<InstanceDetail, InstanceDetail>({
      current: data,
      mutate,
      optimistic: (inst) => ({ ...inst, status: decision === "approve" ? "running" : "failed" }),
      request: () => decideInstance(id, decision, comment),
      settle: (_predicted, updated) => updated,
      toast,
      success: decision === "approve" ? t("instance.toast.approved") : t("instance.toast.rejected"),
    });
    setComment("");
  }

  return (
    <section className="viewer">
      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <>
          <div className="viewer__head">
            <div>
              <h1>{data.workflow_name}</h1>
              <p className="muted latin">{data.id}</p>
            </div>
            <StatusPill status={data.status} />
          </div>

          <BackLink to={`/workflows/${data.workflow_id}`}>{t("instance.openWorkflow")}</BackLink>

          {data.status === "waiting" && (
            <div className="card viewer__decision">
              <span>
                {data.approval?.title || t("instance.awaitingDecision", { node: data.current_node ?? "" })}
              </span>
              {data.approval?.message && <p className="muted">{data.approval.message}</p>}
              <textarea
                className="viewer__decision-comment"
                rows={2}
                placeholder={t("instance.decisionComment")}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
              <div className="viewer__decision-actions">
                <button
                  className="btn btn--primary btn--sm"
                  type="button"
                  onClick={() => decide("approve")}
                >
                  {t("instance.approve")}
                </button>
                <button
                  className="btn btn--danger btn--sm"
                  type="button"
                  onClick={() => decide("reject")}
                >
                  {t("instance.reject")}
                </button>
              </div>
            </div>
          )}

          {data.approval && data.approval.status !== "pending" && (
            <p className="muted viewer__decision-outcome">
              {t("instance.decidedBy", { user: data.approval.decided_by ?? "" })}
              {data.approval.comment && ` — ${data.approval.comment}`}
            </p>
          )}

          {data.error && <p className="error-text">{data.error}</p>}

          <h2>{t("instance.timeline")}</h2>
          <ol className="viewer__timeline">
            {data.node_runs.map((run, i) => (
              <RunCard key={`${run.node_key}-${run.attempt}-${i}`} run={run} />
            ))}
            {data.node_runs.length === 0 && <p className="muted">{t("instance.noRuns")}</p>}
          </ol>
        </>
      )}
    </section>
  );
}

function RunCard({ run }: { run: NodeRun }) {
  const { t } = useTranslation();
  return (
    <li className="card runcard">
      <div className="runcard__head">
        <span className="runcard__key latin">{run.node_key}</span>
        <span className="muted">{t(`nodeType.${run.node_type}`)}</span>
        {run.attempt > 1 && (
          <span className="muted latin">
            {t("instance.attempt")} {run.attempt}
          </span>
        )}
        <StatusPill status={run.status} />
      </div>

      {run.node_type === "assistant_action" && run.status === "completed" && (
        <AssistantStepSummary output={run.output} />
      )}

      {(run.input != null || run.output != null) && (
        <div className="runcard__io">
          {run.input != null && (
            <Payload title={t("instance.input")} value={run.input} />
          )}
          {run.output != null && (
            <Payload title={t("instance.output")} value={run.output} />
          )}
        </div>
      )}

      {run.error && <p className="error-text">{run.error}</p>}

      {run.logs.length > 0 && (
        <ul className="runcard__logs">
          {run.logs.map((log, i) => (
            <li key={i} className={`runcard__log runcard__log--${log.level}`}>
              <span className="runcard__log-level">{t(`instance.logLevel.${log.level}`)}</span>
              <span>
                {t(`instance.log.${log.message}`, { ...(log.data ?? {}), defaultValue: log.message })}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

interface AssistantStepOutput {
  action?: string;
  summary?: string;
  links?: { type: string; value: string; label: string }[];
  trace_id?: string;
}

/**
 * What the assistant step actually produced, read as a sentence rather than JSON: the draft it
 * created, the records it links to, and the trace the AI usage page prices. An `output_key` on the
 * node nests the same shape one level down, so we unwrap that case too.
 */
function AssistantStepSummary({ output }: { output: unknown }) {
  const { t } = useTranslation();
  if (output == null || typeof output !== "object") return null;
  const raw = output as Record<string, unknown>;
  const step: AssistantStepOutput =
    typeof raw.action === "string"
      ? (raw as AssistantStepOutput)
      : ((Object.values(raw).find(
          (v) => v != null && typeof v === "object" && "action" in (v as object),
        ) as AssistantStepOutput | undefined) ?? {});
  if (!step.action) return null;

  return (
    <div className="runcard__assistant">
      <p>
        <span className="muted">{t("instance.assistant.ran")}</span>{" "}
        <span className="latin">{step.action}</span>
      </p>
      {step.summary && <p>{step.summary}</p>}
      {step.links && step.links.length > 0 && (
        <ul className="runcard__assistant-links">
          {step.links.map((link) => (
            <li key={`${link.type}-${link.value}`}>
              {link.label} <span className="muted latin">{link.value}</span>
            </li>
          ))}
        </ul>
      )}
      {step.trace_id && (
        <p className="muted">
          {t("instance.assistant.trace")} <span className="latin">{step.trace_id}</span>
        </p>
      )}
    </div>
  );
}

function Payload({ title, value }: { title: string; value: unknown }) {
  const isPlainObject = value != null && typeof value === "object" && !Array.isArray(value);
  const entries = isPlainObject ? Object.entries(value as Record<string, unknown>) : null;
  return (
    <div className="runcard__payload">
      <span className="muted">{title}</span>
      {entries && entries.length > 0 ? (
        <dl className="runcard__payload-rows">
          {entries.map(([key, v]) => (
            <div className="runcard__payload-row" key={key}>
              <dt className="latin">{key}</dt>
              <dd className="latin">
                <Bdi>{typeof v === "object" ? JSON.stringify(v) : String(v)}</Bdi>
              </dd>
            </div>
          ))}
        </dl>
      ) : (
        <pre className="latin">
          <Bdi>{JSON.stringify(value, null, 2)}</Bdi>
        </pre>
      )}
    </div>
  );
}
