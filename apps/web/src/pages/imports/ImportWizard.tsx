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
import { EmptyState } from "../../components/EmptyState";
import { UploadStep } from "./UploadStep";
import { MappingStep } from "./MappingStep";
import "./imports.css";

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
  | { kind: "stats"; batch: ImportBatch }
  | { kind: "lost" };

function stepFor(phase: Phase): StepKey {
  switch (phase.kind) {
    case "upload":
      return "upload";
    case "map":
      return "map";
    case "resuming":
    case "lost":
    case "stats":
      return "review";
  }
}

/**
 * Upload -> Detect -> Map -> (stats). The last two rail steps (Review, Import) are filled in a
 * later session (FILE_13/14) — the stats summary shown after mapping is this session's stand-in
 * for Review, not the real review grid.
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
        setPhase(batch.status === "mapping" ? { kind: "lost" } : { kind: "stats", batch });
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

  const activeStep = stepFor(phase);
  const activeIndex = STEPS.indexOf(activeStep);

  return (
    <section className="imports-page">
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
        {phase.kind === "stats" && <MappingStep batch={phase.batch} onMapped={onMapped} />}
        {phase.kind === "lost" && (
          <EmptyState
            title={t("imports.wizard.mappingLost.title")}
            hint={t("imports.wizard.mappingLost.hint")}
            action={{ label: t("imports.wizard.startOver"), to: "/imports/new" }}
          />
        )}
      </div>
    </section>
  );
}
