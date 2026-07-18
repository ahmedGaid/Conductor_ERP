import { useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";

import { type OppStage, type Opportunity } from "../../api/crm";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { RowActions } from "../../components/RowActions";
import { formatMinor } from "../../lib/money";
import "./PipelineBoard.css";

// The board's own draggable columns — won/lost are closed, so they never appear as a drop target
// (mirrors the OPEN_STAGES list PipelinePage's inline select already uses).
const BOARD_STAGES: OppStage[] = ["qualifying", "proposal", "negotiation"];

function daysSince(iso: string): number {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return 0;
  return Math.max(0, Math.floor((Date.now() - then) / 86_400_000));
}

interface PipelineBoardProps {
  opportunities: Opportunity[];
  onMove: (opp: Opportunity, stage: OppStage) => void;
}

/**
 * Kanban view of the open pipeline — one column per open stage, cards draggable between them.
 * Drag uses the browser's native HTML5 DnD (no new dependency, no custom pointer tracking needed);
 * every card also carries a keyboard-reachable "move to stage" select as the non-drag fallback, per
 * FILE_18's accessibility rule (drag is an enhancement, never the only road).
 */
export function PipelineBoard({ opportunities, onMove }: PipelineBoardProps) {
  const { t } = useTranslation();
  const [dragId, setDragId] = useState<string | null>(null);
  const [overStage, setOverStage] = useState<OppStage | null>(null);

  function onDragStart(e: DragEvent<HTMLElement>, opp: Opportunity) {
    setDragId(opp.id);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", opp.id);
  }

  function onDrop(e: DragEvent<HTMLElement>, stage: OppStage) {
    e.preventDefault();
    setOverStage(null);
    const id = dragId ?? e.dataTransfer.getData("text/plain");
    setDragId(null);
    const opp = opportunities.find((o) => o.id === id);
    if (opp && opp.stage !== stage) onMove(opp, stage);
  }

  if (opportunities.length === 0) {
    return <EmptyState title={t("crm.pipeline.empty")} hint={t("common.emptyHint")} />;
  }

  return (
    <div className="pipeline-board">
      {BOARD_STAGES.map((stage) => {
        const cards = opportunities.filter((o) => o.stage === stage);
        const sum = cards.reduce((s, o) => s + o.amount_minor, 0);
        return (
          <div
            key={stage}
            className={overStage === stage ? "pipeline-board__col pipeline-board__col--over" : "pipeline-board__col"}
            onDragOver={(e) => {
              e.preventDefault();
              e.dataTransfer.dropEffect = "move";
              if (overStage !== stage) setOverStage(stage);
            }}
            onDragLeave={() => setOverStage((s) => (s === stage ? null : s))}
            onDrop={(e) => onDrop(e, stage)}
          >
            <div className="pipeline-board__head">
              <span className="pipeline-board__title">{t(`crm.stage.${stage}`)}</span>
              <span className="pipeline-board__count muted">{cards.length}</span>
              <span className="pipeline-board__sum muted"><Bdi>{formatMinor(sum)}</Bdi></span>
            </div>

            {cards.length === 0 && (
              <p className="pipeline-board__empty muted">{t("crm.pipeline.emptyColumn")}</p>
            )}

            {cards.map((opp) => (
              <article
                key={opp.id}
                className="pipeline-board__card"
                draggable
                onDragStart={(e) => onDragStart(e, opp)}
                onDragEnd={() => {
                  setDragId(null);
                  setOverStage(null);
                }}
              >
                <div className="pipeline-board__card-head">
                  <span className="latin">{opp.number}</span>
                  <span className="muted">{daysSince(opp.updated_at)}{t("crm.pipeline.daysSuffix")}</span>
                </div>
                <p className="pipeline-board__name">{opp.name}</p>
                {opp.customer_code && <p className="muted latin">{opp.customer_code}</p>}
                <div className="pipeline-board__card-foot">
                  <Bdi>{formatMinor(opp.amount_minor, opp.currency)}</Bdi>
                  <RowActions label={t("crm.pipeline.moveToStage")} className="pipeline-board__move">
                    <select
                      aria-label={t("crm.pipeline.moveToStage")}
                      value={opp.stage}
                      onChange={(e) => {
                        const next = e.target.value as OppStage;
                        if (next !== opp.stage) onMove(opp, next);
                      }}
                    >
                      {BOARD_STAGES.map((s) => (
                        <option key={s} value={s}>{t(`crm.stage.${s}`)}</option>
                      ))}
                    </select>
                  </RowActions>
                </div>
              </article>
            ))}
          </div>
        );
      })}
    </div>
  );
}
