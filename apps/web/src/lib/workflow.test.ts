import { describe, expect, it } from "vitest";
import { historyByStage, workflowFor, type StageHistoryEntry } from "./workflow";

describe("workflowFor (sales)", () => {
  it("marks every stage todo for a brand-new order", () => {
    const steps = workflowFor("sales", "new");
    expect(steps.map((s) => s.state)).toEqual(["current", "todo", "todo", "todo", "todo"]);
  });

  it("marks earlier stages done and the current one current", () => {
    const steps = workflowFor("sales", "delivered");
    expect(steps.map((s) => [s.key, s.state])).toEqual([
      ["create", "done"],
      ["confirm", "done"],
      ["deliver", "done"],
      ["invoice", "current"],
      ["payment", "todo"],
    ]);
  });

  it("marks every stage done once paid", () => {
    const steps = workflowFor("sales", "paid");
    expect(steps.every((s) => s.state === "done")).toBe(true);
  });

  it("appends a cancelled exception step without dropping forward stages", () => {
    const steps = workflowFor("sales", "cancelled");
    const exception = steps.at(-1);
    expect(exception).toEqual({ key: "cancelled", state: "current", exception: true });
    expect(steps).toHaveLength(6);
  });

  it("appends a returned exception step", () => {
    const steps = workflowFor("sales", "returned");
    const exception = steps.at(-1);
    expect(exception).toEqual({ key: "returned", state: "current", exception: true });
  });

  it("falls back to done=1 for an unknown status rather than throwing", () => {
    const steps = workflowFor("sales", "some_future_status_not_yet_known");
    expect(steps[0].state).toBe("done");
    expect(steps[1].state).toBe("current");
  });
});

describe("workflowFor (purchasing)", () => {
  it("uses the receive/bill stage labels, not deliver/invoice", () => {
    const steps = workflowFor("purchasing", "received");
    expect(steps.map((s) => s.key)).toEqual(["create", "confirm", "receive", "bill", "payment"]);
  });
});

describe("historyByStage", () => {
  function entry(stage: string, at: string): StageHistoryEntry {
    return { action: "x", stage, actor_name: "Sara", at, snapshot: null };
  }

  it("keeps the latest entry per stage when history is ordered oldest to newest", () => {
    const history = [
      entry("confirm", "2026-01-01T00:00:00Z"),
      entry("confirm", "2026-01-02T00:00:00Z"),
      entry("deliver", "2026-01-03T00:00:00Z"),
    ];
    const map = historyByStage(history);
    expect(map.confirm.at).toBe("2026-01-02T00:00:00Z");
    expect(map.deliver.at).toBe("2026-01-03T00:00:00Z");
  });

  it("ignores entries with no forward stage", () => {
    const history = [{ action: "comment", stage: null, actor_name: null, at: "t", snapshot: null }];
    expect(historyByStage(history)).toEqual({});
  });
});
