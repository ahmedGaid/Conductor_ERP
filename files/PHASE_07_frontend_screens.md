# Phase 07 — Frontend Screens

## Goal
Build the five screens on the Phase 06 shell, in this order: **dashboard → workflow list → canvas → node config
panel → execution viewer**. Every screen is bilingual + RTL-correct from the first render (no bolt-on i18n).
Visual language = Uber/Base-Web density + Conductor workspace/diff aesthetic, matching the reference dashboard.

## Files to touch
```
apps/web/src/
├── lib/api.ts                  # typed client for the Phase 05 endpoints
├── components/MetricCard.tsx
├── components/DataTable.tsx     # muted headers, hairline rows, status-pill column, ⋯ menu, "View all"
├── components/Chart.tsx         # simple line/bar (recharts), axes mirror in RTL
├── pages/Dashboard.tsx
├── pages/WorkflowList.tsx
├── pages/CanvasEditor.tsx       # React Flow
├── components/NodeConfigPanel.tsx
├── pages/ExecutionViewer.tsx
└── flow/                        # React Flow node/edge renderers (status dot, thin connectors)
scripts/gates/gate07.ts          # component tests (Vitest + Testing Library) + RTL assertions
```

## Status pill mapping (semantic colors only, soft-filled, 8px radius)
`completed→ok` · `running→info` · `waiting→warn` · `failed→err` · `pending→neutral`. Status is **always** a pill, never raw text.

## Screens

### Dashboard (`Dashboard.tsx`) — mirror the reference image
- Greeting + period selector. Row of **metric cards**: label (muted) → large value → delta line with up/down
  arrow in green/red ("12.5% vs last month"), optional corner icon. For MVP, metrics are derived from real
  instance data (counts by status, recent runs) — **no invented finance figures**, label them as workflow metrics
  (Total workflows, Running, Waiting on approval, Failed). A small line chart of runs over time. A right-rail
  "Recent activity / Shortcuts" panel (flips to left-rail in RTL). A "recent instances" table with status pills.

### Workflow list (`WorkflowList.tsx`)
- DataTable: name, version, status pill, node count, last run, ⋯ menu (open in canvas / start instance). "New workflow" action.

### Canvas editor (`CanvasEditor.tsx`) — React Flow, Conductor look
- Create nodes (palette: Start/API/Approval/Condition/Script/End), connect edges, drag to position.
- Nodes are clean cards with a **status dot**; edges are thin connectors; the currently-executing node is subtly highlighted (used in viewer-linked mode).
- **RTL mirroring:** in RTL default flow reads right-to-left; node config panel opens from the logical inline-start side; Start→End reading order follows direction.
- **Save** serializes nodes/edges (+positions, edge `ordering`) and POST/PUTs to the API. Reload re-hydrates identically (round-trip).

### Node config panel (`NodeConfigPanel.tsx`)
- Opens on node select from the inline-start side. Renders a typed form per node type (API: method/url/headers/body
  + `write` toggle; Condition: per-edge JSON-logic; Script: JSON-logic; Approval: label). Writes back into canvas state.

### Execution viewer (`ExecutionViewer.tsx`) — Conductor diff/log panel
- Live-ish (poll `/api/instances/:id`) vertical **timeline** of node executions: node name, status pill, duration,
  attempt count, expandable to show input/output JSON (diff-style). Approval rows show approve/reject actions that
  POST to `/approve`. Instance-level status pill at the top. Currently-executing node highlighted on a mini canvas view.

## Verification (gate:07)
- [ ] Component tests render each screen in both `ar/rtl` and `en/ltr` without layout break (assert computed `dir`, sidebar side, table text-align `start`).
- [ ] Canvas save→reload round-trips a 3-node graph identically (positions + edge ordering preserved) against a test API.
- [ ] StatusPill renders the correct token bg/text for all five statuses; never raw text.
- [ ] Execution viewer shows node-level rows with status pill + duration + attempt, expandable to input/output JSON.
- [ ] Metric cards, data table, command bar visually match the reference structure (snapshot test of DOM/structure) in both directions.
- [ ] gate07 runs the component suite headless; exits 0.

## Done signal
All five screens render, mirror correctly in RTL, the canvas round-trips to the DB, and the execution viewer shows
node-level logs with the Conductor look. `gate:07` is green.
