import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../../app/icons";
import { ApiError } from "../../api/client";
import { uploadImportFile, type ImportProfileHit, type ImportUploadResult } from "../../api/smartImports";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";

interface Detected {
  upload: ImportUploadResult;
  entity: string;
  profile?: ImportProfileHit;
}

// Mirrors erp/imports/detect.py's own "don't bother asking" thresholds — the wizard should read
// a file's confidence the same way the server decided it, not invent a second opinion.
const CLEAR_MIN = 70;
const CLEAR_GAP = 20;

function isClearWinner(candidates: { confidence: number }[]): boolean {
  if (!candidates.length || candidates[0].confidence < CLEAR_MIN) return false;
  if (candidates.length === 1) return true;
  return candidates[0].confidence - candidates[1].confidence >= CLEAR_GAP;
}

function confidenceWord(c: number): "high" | "medium" | "low" {
  if (c >= 90) return "high";
  if (c >= 50) return "medium";
  return "low";
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const { t } = useTranslation();
  const word = confidenceWord(confidence);
  const icon = word === "high" ? "check" : word === "medium" ? "info" : "warning";
  return (
    <span className={`imports-confidence imports-confidence--${word}`}>
      <NavIcon name={icon} />
      {t(`imports.confidence.${word}`)}
    </span>
  );
}

type Stage = "idle" | "uploading" | "error" | "detected";

export function UploadStep({ onDetected }: { onDetected: (d: Detected) => void }) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportUploadResult | null>(null);
  const [selectedEntity, setSelectedEntity] = useState("");
  const [profileAccepted, setProfileAccepted] = useState(false);
  const [profileDismissed, setProfileDismissed] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  function reset() {
    setStage("idle");
    setError(null);
    setResult(null);
    setSelectedEntity("");
    setProfileAccepted(false);
    setProfileDismissed(false);
  }

  async function handleFile(file: File) {
    if (/\.xls$/i.test(file.name) && !/\.xlsx$/i.test(file.name)) {
      setError(t("imports.errors.xlsFormat"));
      setStage("error");
      return;
    }
    setStage("uploading");
    setError(null);
    try {
      const res = await uploadImportFile(file);
      const clear = isClearWinner(res.candidates);
      setResult(res);
      setSelectedEntity(clear ? res.candidates[0].entity : "");
      setProfileAccepted(false);
      setProfileDismissed(false);
      setStage("detected");
    } catch (err) {
      const messageKey =
        err instanceof ApiError && typeof err.data?.message_key === "string"
          ? (err.data.message_key as string)
          : null;
      setError(messageKey ? t(messageKey) : err instanceof Error ? err.message : t("common.error.title"));
      setStage("error");
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  }

  function onPick(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) void handleFile(file);
    e.target.value = "";
  }

  if (stage === "idle") {
    return (
      <div
        className={`imports-dropzone${dragOver ? " imports-dropzone--over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.csv"
          className="visually-hidden"
          onChange={onPick}
          aria-label={t("imports.upload.browseButton")}
        />
        <EmptyState
          icon={<NavIcon name="import" />}
          title={t("imports.upload.dropTitle")}
          hint={t("imports.upload.dropHint")}
          action={{ label: t("imports.upload.browseButton"), onClick: () => inputRef.current?.click() }}
        />
      </div>
    );
  }

  if (stage === "uploading") {
    return (
      <div className="imports-uploading" aria-busy="true" role="status">
        <span className="imports-uploading__bar" aria-hidden="true" />
        <p>{t("imports.upload.uploading")}</p>
      </div>
    );
  }

  if (stage === "error") {
    return <ErrorState message={error} onRetry={reset} />;
  }

  // stage === "detected"
  if (!result) return null;
  const candidates = result.candidates.slice(0, 5);
  const clear = isClearWinner(result.candidates);
  const topEntity = result.candidates[0]?.entity;
  const profileHit =
    selectedEntity && selectedEntity === topEntity && !profileDismissed
      ? result.profile_hits.find((p) => p.entity === selectedEntity)
      : undefined;

  if (candidates.length === 0) {
    return (
      <EmptyState
        icon={<NavIcon name="import" />}
        title={t("imports.detect.noMatch.title")}
        hint={t("imports.detect.noMatch.hint")}
        action={{ label: t("imports.upload.tryAnother"), onClick: reset }}
      />
    );
  }

  function continueToMapping() {
    if (!selectedEntity || !result) return;
    onDetected({
      upload: result,
      entity: selectedEntity,
      profile: profileAccepted ? profileHit : undefined,
    });
  }

  return (
    <div className="imports-detect">
      {clear ? (
        <p className="imports-detect__lede" dir="auto">
          {t("imports.detect.looksLike", { entity: t(candidates[0].label_key) })}
        </p>
      ) : (
        <>
          <p className="imports-detect__lede">{t("imports.detect.candidatesTitle")}</p>
          <ul className="imports-detect__candidates">
            {candidates.map((c) => (
              <li key={c.entity}>
                <label className="imports-detect__candidate">
                  <input
                    type="radio"
                    name="import-entity"
                    value={c.entity}
                    checked={selectedEntity === c.entity}
                    onChange={() => {
                      setSelectedEntity(c.entity);
                      setProfileDismissed(false);
                    }}
                  />
                  <span className="imports-detect__candidate-label">{t(c.label_key)}</span>
                  <ConfidenceBadge confidence={c.confidence} />
                </label>
              </li>
            ))}
          </ul>
        </>
      )}

      {profileHit && (
        <div className="imports-profile-chip">
          {!profileAccepted ? (
            <>
              <span dir="auto">{t("imports.detect.profileHit.offer", { name: profileHit.name })}</span>
              <span className="imports-profile-chip__actions">
                <button type="button" className="btn btn--ghost" onClick={() => setProfileAccepted(true)}>
                  {t("imports.detect.profileHit.use")}
                </button>
                <button type="button" className="btn btn--ghost" onClick={() => setProfileDismissed(true)}>
                  {t("imports.detect.profileHit.dismiss")}
                </button>
              </span>
            </>
          ) : (
            <span dir="auto">{t("imports.detect.profileHit.using", { name: profileHit.name })}</span>
          )}
        </div>
      )}

      <footer className="imports-detect__foot">
        <button
          type="button"
          className="btn btn--primary"
          onClick={continueToMapping}
          disabled={!selectedEntity}
        >
          {t("imports.detect.continue")}
        </button>
      </footer>
    </div>
  );
}
