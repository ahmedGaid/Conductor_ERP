/**
 * Converts between the step-list builder's linear/one-branch UI model and the same
 * nodes/edges graph shape the engine and the existing canvas already use (see
 * erp/workflow/services.py::save_graph). A step list is a *constrained view* over that graph —
 * it can only ever express start -> [steps] -> (one optional if/otherwise) -> ... -> end, so it
 * never emits a shape the engine can't already run.
 */
import type { GraphEdge, GraphNode } from "../api/types";

export type StepType = "approval" | "notification" | "condition" | "assistant_action" | "api_call";

export interface Step {
  key: string;
  type: StepType;
  config: Record<string, unknown>;
  /** At most one branch per step list — enforced by the builder UI never nesting a second one. */
  branch?: { ifTrue: Step[]; otherwise: Step[] };
}

export type { GraphEdge, GraphNode };

function conditionFor(config: Record<string, unknown>): unknown {
  return { [config.operator as string]: [{ var: config.field }, config.value] };
}

export function stepsToGraph(steps: Step[]): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes: GraphNode[] = [{ key: "start", type: "start", config: {}, position: {} }];
  const edges: GraphEdge[] = [];
  let previousKey = "start";

  for (const step of steps) {
    nodes.push({ key: step.key, type: step.type, config: step.config, position: {} });
    edges.push({ source: previousKey, target: step.key, ordering: 0, condition: null });

    if (step.branch) {
      const [trueStep] = step.branch.ifTrue;
      if (trueStep) {
        nodes.push({ key: trueStep.key, type: trueStep.type, config: trueStep.config, position: {} });
        edges.push({ source: step.key, target: trueStep.key, ordering: 0, condition: conditionFor(step.config) });
      }
      edges.push({ source: step.key, target: "end", ordering: 1, condition: null });
      nodes.push({ key: "end", type: "end", config: {}, position: {} });
      return { nodes: dedupe(nodes), edges };
    }
    previousKey = step.key;
  }

  nodes.push({ key: "end", type: "end", config: {}, position: {} });
  edges.push({ source: previousKey, target: "end", ordering: 0, condition: null });
  return { nodes: dedupe(nodes), edges };
}

function dedupe(nodes: GraphNode[]): GraphNode[] {
  const seen = new Set<string>();
  return nodes.filter((n) => (seen.has(n.key) ? false : (seen.add(n.key), true)));
}

export function graphToSteps(nodes: GraphNode[], edges: GraphEdge[]): Step[] {
  const byKey = new Map(nodes.map((n) => [n.key, n]));
  const outEdges = (key: string) => edges.filter((e) => e.source === key).sort((a, b) => a.ordering - b.ordering);

  const steps: Step[] = [];
  let current = outEdges("start")[0]?.target;
  while (current && current !== "end") {
    const node = byKey.get(current);
    if (!node) break;
    const out = outEdges(current);
    if (out.length === 2) {
      const trueEdge = out.find((e) => e.condition !== null);
      steps.push({
        key: node.key,
        type: node.type as Step["type"],
        config: node.config,
        branch: {
          ifTrue:
            trueEdge && trueEdge.target !== "end"
              ? [
                  {
                    key: trueEdge.target,
                    type: byKey.get(trueEdge.target)!.type as Step["type"],
                    config: byKey.get(trueEdge.target)!.config,
                  },
                ]
              : [],
          otherwise: [],
        },
      });
      break; // one branch max — anything after it belongs to Advanced, not this builder
    }
    steps.push({ key: node.key, type: node.type as Step["type"], config: node.config });
    current = out[0]?.target;
  }
  return steps;
}
