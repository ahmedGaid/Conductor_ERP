import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import {
  getImportBatch,
  type ImportBatch,
  type ImportMappingResult,
  type ImportProfileHit,
  type ImportUploadResult,
} from "../../api/smartImports";
import { useDraftRecovery } from "../../hooks/useDraftRecovery";
import { EmptyState } from "../../components/EmptyState";
import { UploadStep } from "./UploadStep";
import { MappingStep } from "./MappingStep";
import { ReviewStep } from "./ReviewStep";
import { RunStep } from "./RunStep";
import "./imports.css";

// Statuses reachable only after the user has actually clicked Import inside Review (or is
// resuming a batch that's mid-run, interrupted, finished, or reversed) — everything else means
// "still reviewing" (or the transient `previewing` step mid-mapping-request).
const RUN_STATUSES = new Set(["running", "paused", "done", "rolled_back", "failed"]);

const STEPS = ["upload", "map", "review", "import"] as const;
type StepKey = (typeof STEPS)[number];

interface Detected {
  upload: ImportUploadResult;
  entity: string;
  profile?: ImportProfileHit;
}

type Phase =
  | { kind: "upload" }
  | { kind: "map"; detected: Detected }
  | { kind: "resuming" }
  | { kind: "review"; batch: ImportBatch }
  | { kind: "run"; batchId: string }
  | { kind: "lost" };

// The WorkSession draft for Smart Import is thin — the ImportBatch (server-side) is the source of
// truth for rows/mapping/progress; the draft only points at it (spec section 5.4). It exists once
// a batch does (upload creates the batch), keyed by workflow_key + related_entity_id = batch id, so
// the /drafts surface can offer "Import in progress" and route straight back to /imports/{id}.
interface ImportDraft {
  step: StepKey;
}
const EMPTY_IMPORT_DRAFT: ImportDraft = { step: "upload" };

function batchIdFor(phase: Phase, urlBatchId: string | undefined): string {
  switch (phase.kind) {
    case "map":
      return phase.detected.upload.batch_id;
    case "review":
      return phase.batch.id;
    case "run":
      return phase.batchId;
    default:
      return urlBatchId ?? "";
  }
}

function stepFor(phase: Phase): StepKey {
  switch (phase.kind) {
    case "upload":
      return "upload";
    case "map":
      return "map";
    case "resuming":
    case "lost":
    case "review":
      return "review";
    case "run":
      return "import";
  }
}

/**
 * Upload -> Detect -> Map -> Review -> Run/Report (session 14's `RunStep`, which renders
 * `ImportReport` itself once the batch reaches `done`/`rolled_back`). Resuming a batch (page
 * reload, or `/imports/{id}` from history) routes by status: `running`/`paused`/`done`/
 * `rolled_back`/`failed` mean the user already clicked Import at some point, so they land on Run;
 * anything else (still `ready`/`previewing`, i.e. reviewed but not yet run) lands back on Review.
 *
 * `AppShell` keys its page providers on `location.pathname` (app-wide, for a clean per-page reset)
 * — ANY pathname change remounts this component and wipes local state/refs. Upload and Map both
 * therefore stay on the one `/imports/new` URL (no navigate between them); the URL only moves to
 * `/imports/{id}` once mapping succeeds, at which point the batch object on the server is the
 * complete, sufficient source of truth — a remount there costs nothing.
 */
export function ImportWizard() {
  const { t } = useTranslation();
  const { id: rawId } = useParams<{ id: string }>();
  const batchId = rawId && rawId !== "new" ? rawId : undefined;
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>(batchId ? { kind: "resuming" } : { kind: "upload" });

  useEffect(() => {
    if (!batchId || phase.kind !== "resuming") return;
    let cancelled = false;
    getImportBatch(batchId)
      .then((batch) => {
        if (cancelled) return;
        // Headers/samples only ever live in the upload response, never persisted on the batch —
        // this path (a batch id already in the URL) only exists once mapping is done, so a
        // "mapping" status here means something went wrong server-side, not a normal reload.
        if (batch.status === "mapping") setPhase({ kind: "lost" });
        else if (RUN_STATUSES.has(batch.status)) setPhase({ kind: "run", batchId: batch.id });
        else setPhase({ kind: "review", batch });
      })
      .catch(() => {
        if (!cancelled) setPhase({ kind: "lost" });
      });
    return () => {
      cancelled = true;
    };
  }, [phase.kind, batchId]);

  const onDetected = useCallback((detected: Detected) => {
    setPhase({ kind: "map", detected });
  }, []);

  const onMapped = useCallback(
    (result: ImportMappingResult) => {
      navigate(`/imports/${result.batch.id}`, { replace: true });
    },
    [navigate],
  );

  const onImported = useCallback((batchId: string) => {
    setPhase({ kind: "run", batchId });
  }, []);

  const activeStep = stepFor(phase);
  const activeIndex = STEPS.indexOf(activeStep);

  // A batch only exists once upload succeeds, so the pointer draft only starts there.
  const activeBatchId = batchIdFor(phase, batchId);
  const recovery = useDraftRecovery<ImportDraft>({
    workflowKey: "imports.smart.create",
    entityType: "import",
    value: { step: activeStep },
    baseline: EMPTY_IMPORT_DRAFT,
    schemaVersion: 1,
    relatedEntityId: activeBatchId,
    enabled: activeBatchId !== "",
  });

  // Once the import actually starts running, the batch itself (visible in Import History) is the
  // durable record — the pointer draft has done its job and must not reappear as "in progress".
  useEffect(() => {
    if (phase.kind === "run") void recovery.complete(phase.batchId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase.kind]);

  return (
    <section
      className={
        phase.kind === "review" || phase.kind === "run" ? "imports-page imports-page--wide" : "imports-page"
      }
    >
      <header className="imports-page__head">
        <h1 className="imports-page__title">{t("imports.wizard.title")}</h1>
        <p className="imports-page__lede">{t("imports.wizard.lede")}</p>
      </header>

      <ol className="imports-rail" aria-label={t("imports.wizard.title")}>
        {STEPS.map((step, i) => {
          const state = i < activeIndex ? "done" : i === activeIndex ? "current" : "upcoming";
          return (
            <li key={step} className={`imports-rail__step imports-rail__step--${state}`}>
              <span className="imports-rail__marker" aria-hidden="true">
                {state === "done" ? (
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="m5 12 5 5 9-10" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  i + 1
                )}
              </span>
              <span className="imports-rail__label">{t(`imports.wizard.steps.${step}`)}</span>
            </li>
          );
        })}
      </ol>

      {phase.kind === "review" || phase.kind === "run" ? (
        // Review/Run build their own bordered surfaces (plan section, summary sidebar, report
        // card) around plain content — one more enclosing card here would nest card-in-card.
        phase.kind === "review" ? (
          <ReviewStep batch={phase.batch} onImported={onImported} />
        ) : (
          <RunStep batchId={phase.batchId} />
        )
      ) : (
        <div className="imports-card card">
          {phase.kind === "upload" && <UploadStep onDetected={onDetected} />}
          {phase.kind === "resuming" && <div className="imports-loading" aria-busy="true" />}
          {phase.kind === "map" && (
            <MappingStep
              upload={phase.detected.upload}
              entity={phase.detected.entity}
              profile={phase.detected.profile}
              onMapped={onMapped}
            />
          )}
          {phase.kind === "lost" && (
            <EmptyState
              title={t("imports.wizard.mappingLost.title")}
              hint={t("imports.wizard.mappingLost.hint")}
              action={{ label: t("imports.wizard.startOver"), to: "/imports/new" }}
            />
          )}
        </div>
      )}
    </section>
  );
}
