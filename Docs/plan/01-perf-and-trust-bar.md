# Session 01 — Performance + trust bar (make "fast & correct" mechanical)

**Goal:** turn "Linear-fast, always-correct" from a vibe into enforced budgets, so every later
feature inherits them. Recall `erp-frontend`. Branch `feat/perf-trust-bar`.

## Why
Speed and trust are the brand. If they aren't measured, they rot. Lock them with gates + budgets
the same way brand is locked by `gate03`.

## Tasks

### A. Backend performance budgets
1. Add a lightweight query-count + latency assertion helper in tests: `assertMaxQueries(n)` around
   each list endpoint (catches N+1). Wire into the existing perf test file
   (`erp/monitoring/tests/test_security_perf.py`).
2. Audit the hot list endpoints (sales orders, inventory on-hand, GL) for N+1 — add
   `select_related`/`prefetch_related`. Set a budget: **list endpoint ≤ 8 queries, p95 < 150ms** on
   seed data. Fail the gate if exceeded.
3. Add DB indexes for the columns every list filters/sorts on (status, branch, created_at, party
   code). Verify with `EXPLAIN` on the seed set.

### B. Frontend speed budgets
1. Add a bundle-size check to `apps/web` (script that fails if main chunk > a set KB budget). No new
   dep — parse `dist` output. Route-split any page over budget (React.lazy) — settings/admin/report
   builder are prime candidates.
2. Confirm hover-prefetch + optimistic primitives are used on every list→detail nav (they exist per
   `erp-frontend`). Add any missing.
3. Add a route-level `<Suspense>` skeleton (designed, not spinner) for lazy routes so perceived load
   stays calm.

### C. Trust / correctness invariants (the money + audit guarantees)
1. Write property-style tests for money: `debits == credits` on every posted journal;
   `net + tax == total` on every invoice; on-hand never negative after any movement sequence. These
   are the "it can never be wrong" tests SMBs pay for.
2. Add an idempotency guarantee test: replaying the same "complete sale" / "receive stock" request
   (same idempotency key) produces exactly one side-effect.
3. Ensure every state-changing action writes an `AuditEntry` with actor + correlation id (spot-check
   3 modules; add where missing).

## Done bar
- Perf gate (query/latency/bundle budgets) added and GREEN.
- Money/on-hand/idempotency invariant tests pass; `gate:all` GREEN.
- Record the budgets in `DECISIONS.md` "Perf budgets 2026-07" so they're not silently relaxed later.
