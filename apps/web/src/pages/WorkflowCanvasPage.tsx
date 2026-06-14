import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import {
  createWorkflow,
  getWorkflow,
  startInstance,
  updateWorkflow,
  type GraphPayload,
} from "../api/workflows";
import type { GraphEdge, GraphNode, NodeType } from "../api/types";
import { NodeConfigPanel, type Selection } from "./canvas/NodeConfigPanel";
import "./WorkflowCanvasPage.css";

type WfNodeData = {
  nodeType: NodeType;
  label: string;
  config: Record<string, unknown>;
  [k: string]: unknown;
};
type WfEdgeData = { condition: unknown | null; ordering: number; [k: string]: unknown };
type WfNode = Node<WfNodeData>;
type WfEdge = Edge<WfEdgeData>;

const PALETTE: NodeType[] = ["start", "approval", "condition", "api_call", "script", "end"];

function edgeId(source: string, target: string, ordering: number): string {
  return `${source}__${target}__${ordering}`;
}

function nodeLabel(node: GraphNode): string {
  const label = (node.config as { label?: unknown })?.label;
  return typeof label === "string" && label ? label : node.key;
}

function toRf(nodes: GraphNode[], edges: GraphEdge[]): { nodes: WfNode[]; edges: WfEdge[] } {
  return {
    nodes: nodes.map((n) => ({
      id: n.key,
      position: { x: Number(n.position?.x ?? 0), y: Number(n.position?.y ?? 0) },
      data: { nodeType: n.type, label: nodeLabel(n), config: n.config ?? {} },
    })),
    edges: edges.map((e) => ({
      id: edgeId(e.source, e.target, e.ordering),
      source: e.source,
      target: e.target,
      label: e.condition ? "⋔" : "",
      data: { condition: e.condition, ordering: e.ordering },
    })),
  };
}

export function WorkflowCanvasPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const [name, setName] = useState(t("workflow.untitled"));
  const [version, setVersion] = useState<number | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<WfNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<WfEdge>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const counter = useRef(0);

  // Load an existing workflow, or seed a brand-new graph with one start node.
  useEffect(() => {
    let active = true;
    if (!id) {
      const seeded = toRf(
        [{ key: "start", type: "start", config: {}, position: { x: 80, y: 80 } }],
        [],
      );
      setNodes(seeded.nodes);
      setEdges(seeded.edges);
      return;
    }
    getWorkflow(id)
      .then((wf) => {
        if (!active) return;
        setName(wf.name);
        setVersion(wf.version);
        const rf = toRf(wf.nodes, wf.edges);
        setNodes(rf.nodes);
        setEdges(rf.edges);
      })
      .catch((err) => active && setError(err instanceof Error ? err.message : String(err)));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => {
        const ordering = eds.filter((e) => e.source === connection.source).length;
        const newEdge: WfEdge = {
          id: edgeId(connection.source, connection.target, ordering),
          source: connection.source,
          target: connection.target,
          label: "",
          data: { condition: null, ordering },
        };
        return addEdge(newEdge, eds) as WfEdge[];
      });
    },
    [setEdges],
  );

  function addNode(type: NodeType) {
    counter.current += 1;
    let key = `${type}_${counter.current}`;
    const taken = new Set(nodes.map((n) => n.id));
    while (taken.has(key)) {
      counter.current += 1;
      key = `${type}_${counter.current}`;
    }
    const newNode: WfNode = {
      id: key,
      position: { x: 200 + (nodes.length % 4) * 40, y: 120 + nodes.length * 30 },
      data: { nodeType: type, label: key, config: {} },
    };
    setNodes((nds) => [...nds, newNode]);
  }

  const selection: Selection = useMemo(() => {
    if (selectedNodeId) {
      const n = nodes.find((x) => x.id === selectedNodeId);
      if (n) return { kind: "node", key: n.id, nodeType: n.data.nodeType, config: n.data.config };
    }
    if (selectedEdgeId) {
      const e = edges.find((x) => x.id === selectedEdgeId);
      if (e) return { kind: "edge", id: e.id, condition: e.data?.condition ?? null, ordering: e.data?.ordering ?? 0 };
    }
    return null;
  }, [selectedNodeId, selectedEdgeId, nodes, edges]);

  function updateNodeConfig(key: string, config: Record<string, unknown>) {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === key
          ? { ...n, data: { ...n.data, config, label: nodeLabel({ key, type: n.data.nodeType, config, position: {} }) } }
          : n,
      ),
    );
    setMessage(t("canvas.applied"));
  }

  function updateEdge(edgeIdToUpdate: string, condition: unknown | null, ordering: number) {
    setEdges((eds) =>
      eds.map((e) =>
        e.id === edgeIdToUpdate
          ? { ...e, label: condition ? "⋔" : "", data: { ...e.data, condition, ordering } }
          : e,
      ),
    );
    setMessage(t("canvas.applied"));
  }

  function deleteSelection() {
    if (selectedNodeId) {
      setNodes((nds) => nds.filter((n) => n.id !== selectedNodeId));
      setEdges((eds) => eds.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId));
      setSelectedNodeId(null);
    } else if (selectedEdgeId) {
      setEdges((eds) => eds.filter((e) => e.id !== selectedEdgeId));
      setSelectedEdgeId(null);
    }
  }

  function buildPayload(): GraphPayload {
    return {
      name: name.trim() || t("workflow.untitled"),
      nodes: nodes.map((n) => ({
        key: n.id,
        type: n.data.nodeType,
        config: n.data.config ?? {},
        position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
      })),
      edges: edges.map((e) => ({
        source: e.source,
        target: e.target,
        condition: e.data?.condition ?? null,
        ordering: e.data?.ordering ?? 0,
      })),
    };
  }

  async function save() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const payload = buildPayload();
      if (id) {
        const wf = await updateWorkflow(id, payload);
        setVersion(wf.version);
        setMessage(t("canvas.saved"));
      } else {
        const wf = await createWorkflow(payload);
        navigate(`/workflows/${wf.id}`, { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function runInstance() {
    if (!id) return;
    setBusy(true);
    setError(null);
    try {
      const instance = await startInstance(id);
      navigate(`/instances/${instance.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="canvas">
      <div className="canvas__toolbar">
        <input
          className="canvas__name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          aria-label={t("workflow.name")}
        />
        {version != null && <span className="muted latin">v{version}</span>}
        <div className="canvas__palette">
          {PALETTE.map((type) => (
            <button key={type} className="btn btn--sm" type="button" onClick={() => addNode(type)}>
              + {t(`nodeType.${type}`)}
            </button>
          ))}
        </div>
        <div className="canvas__toolbar-actions">
          <button className="btn btn--primary btn--sm" type="button" onClick={save} disabled={busy}>
            {t("canvas.save")}
          </button>
          <button
            className="btn btn--sm"
            type="button"
            onClick={runInstance}
            disabled={busy || !id}
            title={!id ? t("canvas.saveFirst") : undefined}
          >
            {t("canvas.run")}
          </button>
        </div>
      </div>

      {message && <p className="canvas__msg">{message}</p>}
      {error && <p className="error-text canvas__msg">{error}</p>}

      <div className="canvas__body">
        {/* The graph keeps an LTR coordinate space; the surrounding chrome mirrors in RTL. */}
        <div className="canvas__flow" dir="ltr">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_, node) => {
              setSelectedNodeId(node.id);
              setSelectedEdgeId(null);
            }}
            onEdgeClick={(_, edge) => {
              setSelectedEdgeId(edge.id);
              setSelectedNodeId(null);
            }}
            onPaneClick={() => {
              setSelectedNodeId(null);
              setSelectedEdgeId(null);
            }}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap pannable zoomable />
          </ReactFlow>
        </div>

        <NodeConfigPanel
          selection={selection}
          onNodeConfigChange={updateNodeConfig}
          onEdgeChange={updateEdge}
          onDelete={deleteSelection}
        />
      </div>
    </section>
  );
}
