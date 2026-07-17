import { test, expect } from "../lib/fixtures";

// Builds the graph via the same `save_graph` contract the canvas UI POSTs (see DECISIONS.md
// "Playwright E2E suite" entry) rather than dragging React Flow edges — a start -> script -> end
// chain computing 2+3, matching the workflow proven live in
// Docs/plan/delivery-readiness/FILE_01_E2E_RESULTS.md Phase 1c. The **Run** step is driven through
// the real UI so the button, the navigation to the instance, and the completion state are all
// exercised for real.
interface WorkflowApi {
  id: string;
}
interface InstanceApi {
  id: string;
  status: string;
  node_runs: { node_key: string; status: string; output: unknown }[];
}

test("workflow: run to completion", async ({ page, t, apiPost, apiGet }) => {
  const workflow = await apiPost<WorkflowApi>("/workflow/workflows", {
    name: `E2E Workflow ${Date.now()}`,
    nodes: [
      { key: "start", type: "start", config: {}, position: { x: 80, y: 80 } },
      {
        key: "script_1",
        type: "script",
        config: { logic: { "+": [2, 3] }, output_key: "sum" },
        position: { x: 280, y: 80 },
      },
      { key: "end", type: "end", config: {}, position: { x: 480, y: 80 } },
    ],
    edges: [
      { source: "start", target: "script_1", condition: null, ordering: 0 },
      { source: "script_1", target: "end", condition: null, ordering: 0 },
    ],
  });

  await page.goto(`/#/workflows/${workflow.id}`);
  await page.getByRole("button", { name: t("canvas.run") }).click();
  await page.waitForURL(/#\/instances\/[0-9a-f-]{36}$/);
  const instanceId = page.url().split("/").pop()!;

  // Scoped to the instance-level status pill (`.viewer__head`) — the same word also appears in
  // per-node run badges, the script node's JSON output, and a log line, all on this one page.
  await expect(page.locator(".viewer__head").getByText(t("status.completed"), { exact: true })).toBeVisible();
  await expect(page.locator(".runcard")).toHaveCount(3);

  // Business-layer check: the script node actually computed 2+3, not just "some" completion.
  const instance = await apiGet<InstanceApi>(`/workflow/instances/${instanceId}`);
  expect(instance.status).toBe("completed");
  const scriptRun = instance.node_runs.find((r) => r.node_key === "script_1");
  expect(scriptRun?.status).toBe("completed");
  expect(scriptRun?.output).toEqual({ sum: 5 });
});
