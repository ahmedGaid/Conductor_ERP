# Phase 05 — Backend API

## Goal
Expose the engine over HTTP: define/save workflows, start instances, submit approvals (resume), and read full
execution history. Single hardcoded dev user (no real auth — forbidden-list item).

## Files to touch
- `apps/api/src/http/auth.ts` — middleware injecting `req.user = { id: DEV_USER_ID, name: DEV_USER_NAME }`
- `apps/api/src/http/validation.ts` — zod schemas for every body
- `apps/api/src/routes/workflows.ts`
- `apps/api/src/routes/instances.ts`
- `apps/api/src/routes/approvals.ts`
- `apps/api/src/routes/logs.ts`
- `apps/api/src/index.ts` — mount routers, error handler, CORS for `WEB_PORT`, mount mock-ERP router
- `apps/api/tests/api.*.test.ts` (supertest)
- `scripts/gates/gate05.ts`

## Endpoints (all JSON; all bodies zod-validated; consistent `{ data } | { error }` envelope)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/api/workflows` | list workflows (id, name, version, status, counts) |
| GET | `/api/workflows/:id` | full graph: nodes + edges |
| POST | `/api/workflows` | create workflow `{ name, nodes[], edges[] }` (validates graph) |
| PUT | `/api/workflows/:id` | replace graph (new `version`, old archived) |
| POST | `/api/workflows/:id/instances` | start instance `{ initialPayload }` → runs to first `waiting`/terminal |
| GET | `/api/instances` | list instances (status, current node, startedBy, timestamps) |
| GET | `/api/instances/:id` | instance + node executions + logs (the execution-viewer payload) |
| POST | `/api/instances/:id/approve` | `{ nodeId, decision: 'approve'\|'reject', comment? }` → `engine.resume` |

## Graph validation (on create/update) — reject bad definitions before they can run
- exactly one `start` node and ≥one `end` node.
- every non-`end` node has ≥one out-edge; every non-`start` node is reachable from `start`.
- `condition` nodes: out-edges carry `condition` JSON; non-condition branching nodes do not have >1 unconditional out-edge.
- edge `ordering` values unique per source node.
- no dangling edge endpoints. Return `400` with a precise message; never persist an invalid graph.

## Start/resume behavior
- `POST .../instances` creates the instance (`pending`), then calls `engine.run(instanceId)` which advances until
  it hits `waiting` (approval) or a terminal state, persisting every transition. Response = current instance snapshot.
- `POST .../approve` validates the target node is the instance's current `waiting` approval node, applies the
  decision, and calls `engine.resume`. Wrong node or non-waiting instance → `409 Conflict` with reason.

## Verification (gate:05)
- [ ] supertest suite green: create→get→start→(waiting)→approve→advance, plus reject branch.
- [ ] Invalid-graph POSTs (two starts / unreachable node / duplicate edge ordering) all return `400`.
- [ ] Approving the wrong node returns `409`.
- [ ] Starting the seeded Purchase-Request workflow returns an instance in `waiting` at `manager_approval`.
- [ ] gate05 boots the app via `createApp()` and runs the suite headless; exits 0.

## Done signal
The engine is fully drivable over HTTP with validated inputs and a clean read model for the UI.
`gate:05` is green.
