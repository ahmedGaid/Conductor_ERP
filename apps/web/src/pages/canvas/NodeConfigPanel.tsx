import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { listAssistantActions } from "../../api/workflows";
import type { AssistantActionOption, NodeType } from "../../api/types";
import { ComboBox } from "../../components/ComboBox";

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
          {selection.nodeType === "approval" && (
            <ApprovalFields
              config={selection.config}
              onChange={(config) => onNodeConfigChange(selection.key, config)}
            />
          )}
          {selection.nodeType === "assistant_action" && (
            <AssistantActionFields
              config={selection.config}
              onChange={(config) => onNodeConfigChange(selection.key, config)}
            />
          )}
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

/**
 * Structured fields for the assistant step: which catalog action runs, and where each of its
 * inputs comes from. Every input is a template over the run — `{{ ctx.customer }}` reads the
 * run's context, `{{ in.code }}` reads the previous step's output — so the mapping is written
 * once by the author and resolved per run.
 *
 * The step runs as whoever *starts* the run, with their permissions checked then; the note below
 * the picker says so, which is why the list itself is not filtered by the author's own roles.
 */
function AssistantActionFields({
  config,
  onChange,
}: {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}) {
  const { t } = useTranslation();
  const [catalog, setCatalog] = useState<AssistantActionOption[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    listAssistantActions()
      .then((rows) => active && setCatalog(rows))
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
    };
  }, []);

  const selectedName = (config.action as string) ?? "";
  const options = useMemo(
    () => catalog.map((a) => ({ value: a.name, label: a.name })),
    [catalog],
  );
  const selected = catalog.find((a) => a.name === selectedName);
  const inputs = (config.inputs as Record<string, string>) ?? {};

  function setAction(name: string) {
    // Keep only the mappings the newly chosen action actually takes — a stale input from the
    // previous action would be silently ignored at run time, which reads as a bug.
    const next = catalog.find((a) => a.name === name);
    const kept = Object.fromEntries(
      Object.entries(inputs).filter(([key]) => next?.args.includes(key)),
    );
    onChange({ ...config, action: name, inputs: kept });
  }

  function setInput(arg: string, value: string) {
    onChange({ ...config, inputs: { ...inputs, [arg]: value } });
  }

  return (
    <>
      <label className="canvas__field">
        <span>{t("canvas.assistant.action")}</span>
        {failed ? (
          <p className="error-text">{t("canvas.assistant.catalogFailed")}</p>
        ) : (
          <ComboBox
            options={options}
            value={selectedName}
            onChange={setAction}
            placeholder={t("canvas.assistant.actionPlaceholder")}
            className="latin"
            aria-label={t("canvas.assistant.action")}
          />
        )}
      </label>

      {selected && <p className="muted canvas__hint">{selected.description}</p>}

      {selected?.args.map((arg) => (
        <label className="canvas__field" key={arg}>
          <span className="latin">{arg}</span>
          <input
            className="latin"
            value={inputs[arg] ?? ""}
            onChange={(e) => setInput(arg, e.target.value)}
            placeholder={t("canvas.assistant.inputPlaceholder")}
          />
        </label>
      ))}

      <label className="canvas__field">
        <span>{t("canvas.assistant.outputKey")}</span>
        <input
          className="latin"
          value={(config.output_key as string) ?? ""}
          onChange={(e) => onChange({ ...config, output_key: e.target.value })}
          placeholder={t("canvas.assistant.outputKeyPlaceholder")}
        />
      </label>

      <p className="muted canvas__hint">{t("canvas.assistant.permissionNote")}</p>
    </>
  );
}

/**
 * Structured fields for the approval node's title/message/role — the fields most authors set.
 * A specific approver (`approver_user_id`) still goes through the raw JSON config below it; a
 * user-search combobox here is a follow-up, not built in this pass.
 */
function ApprovalFields({
  config,
  onChange,
}: {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}) {
  const { t } = useTranslation();

  function set(key: string, value: string) {
    onChange({ ...config, [key]: value });
  }

  return (
    <>
      <label className="canvas__field">
        <span>{t("canvas.approval.title")}</span>
        <input
          value={(config.title as string) ?? ""}
          onChange={(e) => set("title", e.target.value)}
        />
      </label>
      <label className="canvas__field">
        <span>{t("canvas.approval.message")}</span>
        <textarea
          rows={2}
          value={(config.message as string) ?? ""}
          onChange={(e) => set("message", e.target.value)}
        />
      </label>
      <label className="canvas__field">
        <span>{t("canvas.approval.approverRole")}</span>
        <input
          className="latin"
          value={(config.approver_role as string) ?? ""}
          onChange={(e) => set("approver_role", e.target.value)}
          placeholder={t("canvas.approval.approverRolePlaceholder")}
        />
      </label>
    </>
  );
}
