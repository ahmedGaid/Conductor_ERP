import { describe, expect, it } from "vitest";

import { graphToSteps, stepsToGraph, type Step } from "./stepList";

describe("stepsToGraph", () => {
  it("converts a linear step list into a start->step->end graph", () => {
    const steps: Step[] = [
      { key: "notify", type: "notification", config: { recipient: "ahmed" } },
    ];
    const { nodes, edges } = stepsToGraph(steps);
    expect(nodes.map((n) => n.key)).toEqual(["start", "notify", "end"]);
    expect(edges).toEqual([
      { source: "start", target: "notify", ordering: 0, condition: null },
      { source: "notify", target: "end", ordering: 0, condition: null },
    ]);
  });

  it("round-trips through graphToSteps", () => {
    const steps: Step[] = [
      { key: "notify", type: "notification", config: { recipient: "ahmed" } },
    ];
    const { nodes, edges } = stepsToGraph(steps);
    const roundTripped = graphToSteps(
      nodes.map((n) => ({ ...n, position: {} })),
      edges,
    );
    expect(roundTripped).toEqual(steps);
  });
});

describe("stepsToGraph with a branch", () => {
  it("converts one if/otherwise block into a condition node with two out-edges", () => {
    const steps: Step[] = [
      {
        key: "check_amount",
        type: "condition",
        config: { field: "amount_minor", operator: ">", value: 500000 },
        branch: {
          ifTrue: [{ key: "ask_approval", type: "approval", config: { approver_role: "finance_manager" } }],
          otherwise: [],
        },
      },
    ];
    const { nodes, edges } = stepsToGraph(steps);
    expect(nodes.map((n) => n.key)).toEqual(["start", "check_amount", "ask_approval", "end"]);
    const branchEdges = edges.filter((e) => e.source === "check_amount");
    expect(branchEdges).toHaveLength(2);
    expect(branchEdges.find((e) => e.target === "ask_approval")?.condition).toEqual({
      ">": [{ var: "amount_minor" }, 500000],
    });
    expect(branchEdges.find((e) => e.target === "end")?.condition).toBeNull();
  });
});
