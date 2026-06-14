# Phase 02 — Execution Engine (TESTS FIRST)

## Goal
Implement the deterministic, crash-resumable state machine that drives a workflow instance node-by-node,
persisting after every transition, honoring idempotency, retry, and edge-selection rules from the contract (§6).
**Write the tests first, watch them fail, then make them pass.**

## Files to touch
- `apps/api/src/engine/types.ts` — the Node I/O contract types + the `NodeExecutor` interface
- `apps/api/src/engine/idempotency.ts` — `keyFor(instanceId,nodeId,attempt)` = sha256 hex
- `apps/api/src/engine/edges.ts` — deterministic edge selection
- `apps/api/src/engine/engine.ts` — the state machine (`step`, `run`, `resume`)
- `apps/api/src/engine/registry.ts` — maps `NodeType → NodeExecutor` (executors land in Phase 03)
- `apps/api/tests/engine.crash-resume.test.ts`
- `apps/api/tests/engine.idempotency.test.ts`
- `apps/api/tests/engine.edge-selection.test.ts`
- `apps/api/tests/engine.determinism.test.ts`
- `scripts/gates/gate02.ts`

## Contract types (`types.ts`)
```ts
export type RunStatus = 'success' | 'failed' | 'waiting';
export interface NodeInput  { instanceContext: Record<string, unknown>; nodeConfig: unknown; incomingPayload: Record<string, unknown>; }
export interface NodeOutput { status: RunStatus; outputPayload: Record<string, unknown>; error?: string; }
export interface NodeExecutor {
  readonly type: import('@prisma/client').NodeType;
  readonly isExternalWrite: boolean;          // true ⇒ engine enforces idempotency
  run(input: NodeInput): Promise<NodeOutput>; // pure of inputs + ONE declared side effect
}
```

## Engine rules (implement exactly)
1. **One DB transaction per transition.** `prisma.$transaction(async tx => { ... })` wraps:
   create/advance the `NodeExecution` row, update `WorkflowInstance.status/currentNodeId/context`, and write
   `ExecutionLog`. State + transition commit atomically. Never split them (§6.3).
2. **Resume from DB only.** `resume(instanceId)` loads the instance, finds `currentNodeId`, and continues.
   No in-memory queue survives a crash. The test kills the process between nodes and calls `resume`.
3. **Status mapping:** executor `success → NodeExecution.completed`, `waiting → instance.waiting` + exit,
   `failed → NodeExecution.failed`; retry per node `config.maxAttempts` (default 3) UNLESS `isExternalWrite`
   and idempotency cannot be guaranteed → mark `failed`, do not retry (§6.4).
4. **Idempotency:** before an external-write executor runs, compute `key = keyFor(instanceId,nodeId,attempt)`.
   Wrap the side effect so that if an `IdempotencyRecord` with that key exists, return the cached `response`
   instead of calling out again. The adapter (Phase 04) also passes the key to the target. Two layers, both proven by tests.
5. **Edge selection (`edges.ts`):** given a source node's out-edges ordered by `ordering ASC`, evaluate each
   `condition` (JSON-logic) against context. Exactly one truthy winner advances. Zero or ≥2 winners ⇒ throw
   `EdgeSelectionError` → instance `failed` with message naming the node and the count (§6.5). For non-condition
   nodes with a single out-edge, that edge wins; multiple unconditional out-edges from a non-condition node is a definition error → `failed`.
6. **Determinism:** edges always read in `ordering ASC, id ASC`. No `Date.now()`/`Math.random()` influences control flow.
   Timestamps are recorded for audit but never branched on.

## Tests to write FIRST (must fail before the engine exists, pass after)

### `engine.idempotency.test.ts`
- Seed an instance whose current node is an external-write node backed by a stub executor that inserts into
  `erp_external.purchase_orders`. Force the node to run, then simulate a retry with the **same attempt** key.
- **Assert:** exactly **one** row in `purchase_orders`; second call returns the cached response; one `IdempotencyRecord`.

### `engine.crash-resume.test.ts`
- Build a 4-node linear flow with a stub executor that records each visit. Run until node 2 commits, then
  **discard the in-memory engine instance entirely** (simulate crash). Construct a fresh engine and call `resume(instanceId)`.
- **Assert:** the flow completes; each node's `NodeExecution` appears exactly once; visit order is `[1,2,3,4]`; no duplicates; final instance `completed`.

### `engine.edge-selection.test.ts`
- Condition node with two out-edges. Case A: exactly one matches → advances to it. Case B: zero match → instance `failed`, error mentions "0 edges". Case C: two match → instance `failed`, error mentions "2 edges". Never picks arbitrarily.

### `engine.determinism.test.ts`
- Run the same definition + same inputs + a deterministic stub adapter twice. **Assert** identical node-visit
  sequence and identical final `context` JSON (deep-equal). Re-order edge insertion in the DB but keep `ordering`;
  assert the path is unchanged (proves ordering, not insertion order, governs flow).

## Verification (gate:02)
- [ ] `vitest run` passes all four engine test files.
- [ ] gate02.ts asserts the four test files exist and that `vitest run tests/engine.*` exits 0.
- [ ] Grep gate: engine source contains **no** `Math.random` and no `Date.now()` used inside control-flow
      (timestamps allowed only in audit writes) — gate greps `src/engine` and fails on a control-flow violation.
- [ ] Approval path: a `waiting` instance persists and `resume(instanceId, {decision:'approve'})` continues; `reject` routes to the rejected edge/branch.

## Done signal
Crash-resume, idempotency, single-edge selection, and determinism are all proven by passing tests.
The engine never holds authoritative state in memory. `gate:02` is green.
