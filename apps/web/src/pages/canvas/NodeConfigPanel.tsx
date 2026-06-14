import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { NodeType } from "../../api/types";

export interface SelectedNode {
  kind: "node";
  key: string;
  nodeType: NodeType;
  config: Record<string, unknown>;
}

export interface SelectedEdge {
  kind: "edge";
  id: string;
  condition: unknown | null;
  ordering: number;
}

export type Selection = SelectedNode | SelectedEdge | null;

interface Props {
  selection: Selection;
  onNodeConfigChange: (key: string, config: Record<string, unknown>) => void;
  onEdgeChange: (id: string, condition: unknown | null, ordering: number) => void;
  onDelete: () => void;
}

/** Inspector for the selected node or edge. Config / condition are edited as JSON. */
export function NodeConfigPanel({ selection, onNodeConfigChange, onEdgeChange, onDelete }: Props) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState("");
  const [ordering, setOrdering] = useState(0);
  const [jsonError, setJsonError] = useState<string | null>(null);

  useEffect(() => {
    setJsonError(null);
    if (!selection) {
      setDraft("");
      return;
    }
    if (selection.kind === "node") {
      setDraft(JSON.stringify(selection.config ?? {}, null, 2));
    } else {
      setDraft(selection.condition == null ? "" : JSON.stringify(selection.condition, null, 2));
      setOrdering(selection.ordering);
    }
  }, [selection]);

  if (!selection) {
    return (
      <aside className="canvas__panel">
        <p className="muted">{t("canvas.selectHint")}</p>
      </aside>
    );
  }

  function apply() {
    setJsonError(null);
    if (selection!.kind === "node") {
      try {
        const parsed = draft.trim() === "" ? {} : JSON.parse(draft);
        onNodeConfigChange(selection!.key, parsed);
      } catch {
        setJsonError(t("canvas.invalidJson"));
      }
    } else {
      try {
        const parsed = draft.trim() === "" ? null : JSON.parse(draft);
        onEdgeChange(selection!.id, parsed, ordering);
      } catch {
        setJsonError(t("canvas.invalidJson"));
      }
    }
  }

  return (
    <aside className="canvas__panel">
      {selection.kind === "node" ? (
        <>
          <h2>{t("canvas.nodeInspector")}</h2>
          <dl className="canvas__props">
            <dt>{t("canvas.nodeKey")}</dt>
            <dd className="latin">{selection.key}</dd>
            <dt>{t("canvas.nodeType")}</dt>
            <dd>{t(`nodeType.${selection.nodeType}`)}</dd>
          </dl>
          <label className="canvas__field">
            <span>{t("canvas.config")}</span>
            <textarea
              className="latin canvas__json"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={8}
              spellCheck={false}
            />
          </label>
        </>
      ) : (
        <>
          <h2>{t("canvas.edgeInspector")}</h2>
          <label className="canvas__field">
            <span>{t("canvas.condition")}</span>
            <textarea
              className="latin canvas__json"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={6}
              spellCheck={false}
              placeholder={t("canvas.conditionPlaceholder")}
            />
          </label>
          <label className="canvas__field">
            <span>{t("canvas.ordering")}</span>
            <input
              type="number"
              value={ordering}
              onChange={(e) => setOrdering(Number(e.target.value))}
            />
          </label>
        </>
      )}

      {jsonError && <p className="error-text">{jsonError}</p>}

      <div className="canvas__panel-actions">
        <button className="btn btn--primary btn--sm" type="button" onClick={apply}>
          {t("canvas.applyChanges")}
        </button>
        <button className="btn btn--danger btn--sm" type="button" onClick={onDelete}>
          {t("common.delete")}
        </button>
      </div>
    </aside>
  );
}
