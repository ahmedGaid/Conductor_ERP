# Phase 04 — Integration Adapters + Mock ERP

## Goal
Implement exactly three adapters behind one interface (REST, SQL/PL-SQL, Webhook) plus a local **mock ERP**
server so the reference flow makes a *real* HTTP call and the idempotency test hits a real UNIQUE constraint.

## Files to touch
- `apps/api/src/adapters/types.ts` — the shared `Adapter` interface
- `apps/api/src/adapters/rest.ts`
- `apps/api/src/adapters/sql.ts`
- `apps/api/src/adapters/webhook.ts`
- `apps/api/src/adapters/index.ts` — `getAdapter(kind)` factory
- `apps/api/src/mock/erp.ts` — Express router mounted at `/mock-erp` and `/mock-sink`
- `apps/api/tests/adapters.*.test.ts`
- `scripts/gates/gate04.ts`

## Shared interface (`types.ts`)
```ts
export interface AdapterCall {
  idempotencyKey?: string;            // present ⇒ adapter MUST dedupe the write
  payload: Record<string, unknown>;
  config: unknown;                    // adapter-specific, zod-validated inside the adapter
}
export interface AdapterResult { ok: boolean; data?: unknown; error?: string; status?: number; }
export interface Adapter {
  readonly kind: 'rest' | 'sql' | 'webhook';
  call(input: AdapterCall): Promise<AdapterResult>;
}
```
The engine/executors never branch on `kind`; they take an `Adapter` and call `.call()`.

## REST adapter (`rest.ts`)
- Config (zod): `{ method, url, headers?, body? }`.
- Uses global `fetch`. When `idempotencyKey` present, send header `Idempotency-Key: <key>`.
- Map HTTP status → `AdapterResult` (`ok = status in 200..299`). Timeout via `AbortController` (default 10s).
- No retry here — retry/idempotency policy lives in the engine (§6).

## SQL / PL-SQL adapter (`sql.ts`)
- Config (zod): `{ statement: string; params?: unknown[]; }`.
- Uses the `pg` Pool against `DATABASE_URL` (targets the `erp_external` schema for the demo).
- **Parameterized ONLY.** `pool.query(text, params)` with `$1,$2,...`. gate04 greps `sql.ts` and FAILS if it finds
  string concatenation/template-literals building SQL (`+ '` near SQL, or `${` inside a query string). No exceptions (§ brief).
- Returns `rows` in `data`. On error → `{ ok:false, error }`.

## Webhook adapter (`webhook.ts`)
- Config (zod): `{ url, headers? }`. Outbound `POST` of `payload` as JSON. Same `Idempotency-Key` behavior as REST.

## Mock ERP (`mock/erp.ts`) — local, deterministic
- `GET /mock-erp/budget?amount=` → `{ approved: amount <= 50000 }` (deterministic, no randomness).
- `POST /mock-erp/po` (the **write**): reads `Idempotency-Key` header; inserts into `erp_external.purchase_orders`
  using `ON CONFLICT (idempotency_key) DO NOTHING RETURNING *`. If conflict (already inserted), `SELECT` the existing
  row and return it with `200`. New insert returns `201`. This makes idempotency provable at the DB layer.
- `POST /mock-sink/notify` → records the call in-memory and returns `{ received: true }` (the supplier notification target).
Mount this router on the same Express app in dev so the reference flow's HTTP calls are real loopback calls.

## Tests
- `adapters.rest.test.ts`: success 2xx, failure 5xx mapping, Idempotency-Key header forwarded.
- `adapters.sql.test.ts`: parameterized SELECT/INSERT against `erp_external`; injection attempt via param is inert.
- `adapters.webhook.test.ts`: POST body + headers; non-2xx → `ok:false`.
- `adapters.idempotency.e2e.test.ts`: call `POST /mock-erp/po` twice with the same key ⇒ **one** DB row, identical response.

## Verification (gate:04)
- [ ] `vitest run tests/adapters.*` exits 0.
- [ ] gate04 greps `sql.ts`: no concatenated SQL; only parameterized queries → fail otherwise.
- [ ] gate04 hits the running mock ERP: same-key double POST yields exactly one `purchase_orders` row.
- [ ] `getAdapter('rest'|'sql'|'webhook')` returns the right `Adapter`; unknown kind throws.

## Done signal
Three adapters share one interface, SQL is strictly parameterized, and idempotent writes are proven against a
real UNIQUE constraint. `gate:04` is green.
