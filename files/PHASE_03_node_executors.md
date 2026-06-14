# Phase 03 — Node Executors

## Goal
Implement one executor per node type behind the single `NodeExecutor` interface from Phase 02, register them,
and unit-test each in isolation. The engine must depend only on the interface — never on a concrete executor.

## Files to touch
- `apps/api/src/executors/start.ts`
- `apps/api/src/executors/apiCall.ts`
- `apps/api/src/executors/approval.ts`
- `apps/api/src/executors/condition.ts`
- `apps/api/src/executors/script.ts`
- `apps/api/src/executors/end.ts`
- `apps/api/src/engine/registry.ts` — register all six
- `apps/api/src/lib/template.ts` — `{{ctx.path}}` resolver against instance context (no eval)
- `apps/api/src/lib/jsonlogic.ts` — wrapper around `json-logic-js`
- `apps/api/tests/executors.*.test.ts` (one per executor)
- `scripts/gates/gate03.ts`

## Per-executor spec

### Start (`start`, isExternalWrite=false)
Seeds context from the instance's initial payload. `run` returns `{ status:'success', outputPayload: incomingPayload }`.
Always exactly one out-edge.

### API Call (`api_call`, isExternalWrite = config.write === true)
- Config (zod-validated): `{ method, urlTemplate, headersTemplate?, bodyTemplate?, write?: boolean, maxAttempts?: number }`.
- Resolves templates via `lib/template.ts` against `{ ctx: instanceContext, in: incomingPayload }`.
- Delegates the HTTP call to the **REST adapter** (Phase 04) — does NOT call `fetch` directly. Returns adapter
  result as `outputPayload`. On non-2xx → `{ status:'failed', error }`.
- When `write === true` the executor reports `isExternalWrite = true` so the engine wraps it in idempotency (§6.4).

### Approval (`approval`, isExternalWrite=false)
- `run` returns `{ status:'waiting', outputPayload:{} }` immediately. The engine persists `waiting` and exits.
- Resume is driven by the API in Phase 05 calling `engine.resume(instanceId, { decision })`. The executor exposes a
  pure helper `applyDecision(decision: 'approve'|'reject')` that writes `{ approved: boolean }` into the node output
  so downstream Condition edges can branch on `manager_approval.approved`.

### Condition (`condition`, isExternalWrite=false)
- Config: `{}` (the branching logic lives on the **edges'** `condition` JSON, per Phase 01).
- `run` returns `{ status:'success', outputPayload: incomingPayload }`; the engine then runs `edges.select()`.
- Keep edge evaluation in the engine (Phase 02), not here, so "exactly one winner" is enforced centrally.

### Script (`script`, isExternalWrite=false) — NOT arbitrary code
- Config: `{ logic: <json-logic object> }`. Evaluate with `json-logic-js` ONLY against context.
- **Hard ban:** no `eval`, no `Function`, no `vm`, no `require` at runtime. gate03 greps the file and fails on any of these.
- Returns the computed value merged into `outputPayload` under a configured key.

### End (`end`, isExternalWrite=false)
- Config: `{ outcome?: 'completed'|'closed' }`. Sets terminal state; engine marks the instance `completed`.

## Registry
`registry.ts` exports `getExecutor(type): NodeExecutor` from a frozen map. Adding a node type later means adding
one file + one map entry; the engine code does not change.

## Verification (gate:03)
- [ ] Each executor has a unit test exercising success + (where relevant) failure/waiting paths with stubbed adapters.
- [ ] `template.ts` test: `{{ctx.amount}}` resolves; missing path yields a clear error, never `undefined`-injection.
- [ ] `script.ts` contains none of `eval(`, `new Function`, `require(`, `vm.` (gate greps and fails otherwise).
- [ ] `vitest run tests/executors.*` exits 0.
- [ ] Type check confirms every executor satisfies `NodeExecutor`; registry returns all six types.

## Done signal
All six node types run through the shared interface; Script is sandboxed to JSON-logic; the engine remains
decoupled from concrete executors. `gate:03` is green.
