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
  | { kind: "resuming" }
  | { kind: "map"; detected: Detected }
  | { kind: "stats"; batch: ImportBatch }
  | { kind: "lost" };

function stepFor(phase: Phase): StepKey {
  switch (phase.kind) {
    case "upload":
    case "resuming":
    case "lost":
      return "upload";
    case "map":
      return "map";
    case "stats":
      return "review";
  }
}

/**
 * Upload -> Detect -> Map -> (stats). The last two rail steps (Review, Import) are filled in a
 * later session (FILE_13/14) — the stats summary shown after mapping is this session's stand-in
 * for Review, not the real review grid.
 */
export function ImportWizard() {
  const { t } = useTranslation();
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>(id ? { kind: "resuming" } : { kind: "upload" });

  useEffect(() => {
    if (!id) {
      setPhase({ kind: "upload" });
      return;
    }
    setPhase((cur) => {
      if (cur.kind === "map" && cur.detected.upload.batch_id === id) return cur;
      if (cur.kind === "stats" && cur.batch.id === id) return cur;
      return { kind: "resuming" };
    });
  }, [id]);

  useEffect(() => {
    if (phase.kind !== "resuming" || !id) return;
    let cancelled = false;
    getImportBatch(id)
      .then((batch) => {
        if (cancelled) return;
        // Headers/samples only ever live in the upload response, never persisted on the batch —
        // a hard reload mid-mapping can't reconstruct the mapping table, only what came after it.
        setPhase(batch.status === "mapping" ? { kind: "lost" } : { kind: "stats", batch });
      })
      .catch(() => {
        if (!cancelled) setPhase({ kind: "lost" });
      });
    return () => {
      cancelled = true;
    };
  }, [phase.kind, id]);

  const onDetected = useCallback(
    (detected: Detected) => {
      setPhase({ kind: "map", detected });
      navigate(`/imports/${detected.upload.batch_id}`, { replace: true });
    },
    [navigate],
  );

  const onMapped = useCallback((result: ImportMappingResult) => {
    setPhase({ kind: "stats", batch: result.batch });
  }, []);

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
