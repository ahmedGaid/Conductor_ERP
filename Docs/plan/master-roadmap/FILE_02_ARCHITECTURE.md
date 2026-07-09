# D2 — Architecture & Scalability

> Keep the modular monolith honest, then make it multi-tenant and horizontally scalable —
> without a microservices detour. Owners already in flight: agentic OS layers →
> `Docs/plan/os-foundations-plan/` (queue 7, created when reached); legacy tenancy spec →
> `Docs/plan/06-saas-multitenancy.md` (superseded in parts — D2.P3 re-anchors it).

---

## Phase D2.P1 — Boundary discipline (cheap, do early)

### D2.P1.T1 — App-boundary import gate
**Status:** todo · **Model:** Sonnet
**Objective:** a gate script that fails when one Django app imports another app's internals (anything not exposed via its `services/` or `contracts/` package).
**Rationale:** the monolith stays modular only if boundaries are mechanical, not tribal knowledge. Weak agents WILL cross-import without this.
**Prerequisites:** none. NO new dependency (no import-linter) — write it with `ast` stdlib.
**Steps:**
1. Write `scripts/gates/gate15.py`: walk `erp/*/`, parse imports with `ast`, allow `erp.<other>.services|contracts|events|errors`, deny everything else cross-app; allowlist file for grandfathered violations (`scripts/gates/gate15_allow.txt`), each line `path -> import`.
2. Run once, seed the allowlist with current violations (do NOT fix them here).
3. Register in `scripts/gates/_run.py`; document the rule in `Docs/ARCHITECTURE.md` (create D2.P1.T2's stub if absent).
**Architecture decisions:** allowlist shrinks-only (gate fails if a listed violation disappears but the line stays — keeps it honest); `erp/core` importable by all.
**Affected files:** `scripts/gates/gate15.py` (new), `scripts/gates/gate15_allow.txt` (new), `scripts/gates/_run.py`.
**Acceptance criteria:** gate green on current tree with seeded allowlist; adding a test violation makes it fail with a message naming file, line, and the allowed alternatives.
**Testing:** run gate; temporary violation file → fails → remove.
**DoD:** gates green, status flipped.

### D2.P1.T2 — ARCHITECTURE.md (the one-page system map)
**Status:** todo · **Model:** Sonnet
**Objective:** a single `Docs/ARCHITECTURE.md`: app inventory with one-line responsibility each, layering rule (api → services → repositories → domain), cross-app communication rules (services/contracts/events only), request lifecycle, and where money/RBAC/audit are enforced.
**Rationale:** the "hidden context" killer — every weak agent session gets pointed here instead of re-exploring.
**Prerequisites:** D2.P1.T1 (rules must match the gate).
**Steps:** 1. `codegraph_explore` per app for its public surface. 2. Write the doc ≤200 lines, link from `CLAUDE.md` source-of-truth map. 3. Add a Mermaid module diagram (renderable on GitHub).
**Architecture decisions:** doc describes what IS, not aspirations; aspirational items live in this roadmap.
**Affected files:** `Docs/ARCHITECTURE.md` (new), `CLAUDE.md` (one line).
**Acceptance criteria:** every `erp/*` app appears; a new engineer can trace one request end-to-end from the doc alone.
**Testing:** n/a (doc) — peer check via D13 review checklist.
**DoD:** committed, status flipped.

### D2.P1.T3 — Domain events audit + outbox decision
**Status:** todo · **Model:** Opus
**Objective:** inventory current in-process events (`erp/*/events.py`), then write the DECISIONS entry choosing the transactional-outbox pattern for reliable side-effects (notifications, webhooks, search indexing) — design only.
**Rationale:** D9 webhooks and D12 tenant events need at-least-once delivery; choosing late means rework.
**Prerequisites:** D2.P1.T2.
**Steps:** 1. List all event producers/consumers via codegraph. 2. Write design: `erp/core` outbox table (id, topic, payload JSON, created, delivered, attempts), writer inside the same transaction as the domain write, deliverer as management-command loop (no broker — no new dependency). 3. DECISIONS entry; implementation task appended as D2.P2.T3 when approved.
**Architecture decisions:** DECISION-GATED: broker (Redis/Celery) explicitly deferred; command-loop first.
**Affected files:** `DECISIONS.md`, this file (append implementation task).
**Acceptance criteria:** decision recorded with reversal condition ("adopt broker when >N events/min sustained").
**Testing:** n/a.
**DoD:** entry committed, status flipped.

## Phase D2.P2 — Performance floor (single-tenant)

### D2.P2.T1 — N+1 and query budget gate
**Status:** todo · **Model:** Sonnet
**Objective:** pytest fixture asserting query counts on the top 10 list/detail endpoints (budget file), failing on regression.
**Rationale:** "Telegram's calm" dies by a thousand N+1s; perf bar already sketched in `Docs/plan/01-perf-and-trust-bar.md` — this is its enforcement half.
**Prerequisites:** none. Read plan 01 first; reuse its budget numbers if set.
**Steps:** 1. `erp/core/tests/query_budget.py` helper: `with assert_max_queries(n)`. 2. `Docs/plan/perf-budgets.md` table endpoint→budget. 3. Apply to sales orders list, invoice detail, inventory list, partner list, journal list + 5 more from usage. 4. Fix violations found (select_related/prefetch only — no caching yet).
**Architecture decisions:** budgets live in the test file next to numbers; caching deferred to D2.P2.T2.
**Affected files:** `erp/core/tests/query_budget.py` (new), per-app test files, touched repositories.
**Acceptance criteria:** all 10 endpoints under budget; budgets documented.
**Testing:** `pytest erp -k query_budget`.
**DoD:** gates green, status flipped.

### D2.P2.T2 — Read-path caching with explicit invalidation
**Status:** todo · **Model:** Sonnet
**Objective:** per-process LRU/local-memory cache for hot reference data (chart of accounts, units, tax rates, settings) with event-driven invalidation; NO cross-request stale money data.
**Rationale:** cheap latency win before any infra spend.
**Prerequisites:** D2.P1.T3 (events inventory), D2.P2.T1.
**Steps:** 1. `erp/core/cache.py`: typed `cached_reference(key, loader, invalidate_on=[events])`. 2. Apply to the 4 reference sets above. 3. Invalidation wired to existing save paths. 4. Never cache documents/balances (rule in ARCHITECTURE.md).
**Architecture decisions:** Django local-memory backend only (single process dev; per-worker in prod is acceptable staleness ≤ TTL 60s for reference data); Redis DECISION-GATED for D2.P3.
**Affected files:** `erp/core/cache.py` (new), reference loaders, `Docs/ARCHITECTURE.md`.
**Acceptance criteria:** repeat request serves from cache (query count 0 for reference set); editing a tax rate invalidates within same process.
**Testing:** unit tests for hit/invalidate; query-budget tests still green.
**DoD:** gates green, status flipped.

## Phase D2.P3 — Multi-tenancy (arp Phase F; entry gate = FOUNDER_PLAN Phase 3)

> Do NOT start before the strategy gate. Legacy spec `06-saas-multitenancy.md` is the base;
> tasks below re-anchor its decisions. One plan folder (`cloud-tenancy-plan/`) gets created
> via ag-plan when reached; tasks here are its charter.

### D2.P3.T1 — Tenancy model decision (charter)
**Status:** todo · **Model:** Opus
**Objective:** DECISIONS entry fixing the tenancy architecture: shared DB + `tenant_id` FK on every tenant-owned table + Postgres RLS as backstop (recommended), vs schema-per-tenant.
**Rationale:** biggest irreversible choice in the company's technical life; must be written, argued, and gated before any code.
**Prerequisites:** D5.P1 complete (data-scope enforcement real), D2.P1.T1 green.
**Steps:** 1. Read plan 06 + FOUNDER_PLAN §5. 2. Write the comparison against OUR facts (SMB count target 50k, Egyptian data-residency, self-hosted premium tier must keep working from the same code). 3. Decision + migration strategy sketch + RLS policy sample. 4. Founder sign-off recorded.
**Architecture decisions:** the entry itself. Self-hosted = tenancy is config (single-tenant mode), same code.
**Affected files:** `DECISIONS.md`, `Docs/ARCHITECTURE.md`.
**Acceptance criteria:** entry names the choice, the loser, the reversal cost, and the RLS backstop plan.
**Testing:** n/a.
**DoD:** founder-approved entry committed.

### D2.P3.T2 — Tenant context plumbing (first code slice)
**Status:** todo · **Model:** Opus then Sonnet
**Objective:** `tenant_id` column + middleware-resolved tenant context + manager-level automatic filtering on 3 pilot apps (identity, sales, accounting), RLS policies for the same.
**Rationale:** prove the pattern end-to-end small before the fleet-wide rollout.
**Prerequisites:** D2.P3.T1 approved.
**Steps:** per the decision entry; ends with a cross-tenant leak test suite (attempt every pilot endpoint as tenant B against tenant A's rows → 404/empty, never 500/data).
**Architecture decisions:** default manager filters ALWAYS; `objects_all_tenants` explicit + audited; RLS as second wall.
**Affected files:** `erp/core/` (tenant model, middleware, manager mixin), pilot apps' models/migrations/repositories, leak test suite.
**Acceptance criteria:** leak suite green; single-tenant mode unaffected (config flag).
**Testing:** `pytest erp` full; dedicated `pytest erp -k tenant_leak`.
**DoD:** gates green, merged behind config flag, status flipped; fleet rollout tasks appended per app.
