# D8 — Data Platform & Database

> Postgres is the platform. Existing owner: reporting/BI layer → `Docs/plan/05-reports-and-bi.md`
> (re-anchor before executing, same rule as all 2026-07-02 legacy plans). This domain adds the
> database correctness/performance floor and the read-model layer reports ride on. Retrieval/RAG
> data → `rag-knowledge-plan` (queue 2), NOT here.

---

## Phase D8.P1 — Schema correctness floor

### D8.P1.T1 — Constraint & index audit
**Status:** todo · **Model:** Sonnet
**Objective:** systematic pass over all apps' models: every FK has the right `on_delete` (PROTECT for anything referenced by posted documents), money fields are integer types with non-null defaults, natural uniqueness enforced (`unique_together`/constraints for number+series+tenant-ready), FK + common-filter indexes exist; findings fixed via migrations.
**Rationale:** ORM defaults (CASCADE, nullable) silently violate ledger integrity; indexes decide whether D2.P2 budgets are winnable.
**Prerequisites:** D2.P2.T1 helpful (budgets reveal missing indexes) but not blocking.
**Steps:** 1. Script `scripts/audit_schema.py`: introspect models, report violations of the four rule classes into a table. 2. Review table with founder-level judgment ONLY where a rule exception seems intended; record exceptions inline in models as comments. 3. Fix via one migration per app. 4. Keep the script as a warn-gate.
**Architecture decisions:** PROTECT is the default `on_delete` for document-referenced masters — deletion goes through archival (D8.P2.T2), never cascade.
**Affected files:** `scripts/audit_schema.py` (new), per-app models + migrations, `_run.py`.
**Acceptance criteria:** audit script reports zero unexplained violations; full pytest green after migrations.
**Testing:** `pytest erp` full; audit script clean.
**DoD:** gates green, status flipped.

### D8.P1.T2 — Query performance instrumentation
**Status:** todo · **Model:** Sonnet
**Objective:** dev-mode slow-query log (>100ms) with correlation id + endpoint, and a `manage.py explain_hot` command running `EXPLAIN ANALYZE` on the top-10 endpoint queries from D2.P2.T1's budget list, saving baselines under `Docs/plan/master-roadmap/perf-baselines/`.
**Rationale:** perf work without baselines is guessing; baselines make regressions arguable in a PR.
**Prerequisites:** D2.P2.T1 (endpoint list exists), D7.P3.T3 (structured logs).
**Steps:** 1. Slow-query middleware/logger extension. 2. Command with the endpoint→queryset registry. 3. Commit initial baselines with dates.
**Affected files:** `erp/core/` logging extension, `erp/core/management/commands/explain_hot.py` (new), baselines dir.
**Acceptance criteria:** command produces plans for all listed queries; slow-query line appears for an artificially slow view.
**Testing:** unit test the middleware threshold; run command.
**DoD:** gates green, status flipped.

## Phase D8.P2 — Lifecycle & volume

### D8.P2.T1 — Data retention & archival policy
**Status:** todo · **Model:** Opus (policy) then Sonnet
**Objective:** written policy + implementation: posted documents are never deleted; masters get `archived_at` soft-archive (hidden from pickers, visible in history); attachment/file retention rules; assistant conversation retention (default 12 months, configurable); audit trail retained forever.
**Rationale:** Egyptian tax law requires years of retention; customers will ask "can I delete"; the answer must be designed, not improvised. GDPR-style erasure requests need a documented stance before cloud.
**Prerequisites:** D5.P2.T4 (audit immutability).
**Steps:** 1. Policy doc `Docs/patterns/data-retention.md` (include the legal-hold note: verify Egyptian statutory retention periods with the accountant before finalizing numbers — BLOCKER-able). 2. `archived_at` mixin in `erp/core`, applied to masters; pickers filter it. 3. Assistant retention task (scheduled command). 4. UI: archive/unarchive actions with designed states.
**Architecture decisions:** soft-archive only; hard-delete exists solely for never-referenced drafts.
**Affected files:** policy doc (new), `erp/core/models.py` mixin, master models + migrations, picker queries, web list pages (archive action), locales, tests.
**Acceptance criteria:** archived product absent from sale form picker, present in old documents and reports; policy doc reviewed by founder.
**Testing:** pytest archive behavior; web gates.
**DoD:** gates + checklist, status flipped.

### D8.P2.T2 — Volume readiness test
**Status:** todo · **Model:** Sonnet
**Objective:** a load-shaped seed (`seed_demo --scale=50`: ~50k documents, 3 years) + rerun of query budgets and `explain_hot` against it; regressions fixed or filed as tasks with baselines attached.
**Rationale:** SMB-year data volumes are known; meeting them BEFORE customers is cheap, after is a fire.
**Prerequisites:** D6.P2.T3 (seed), D8.P1.T2 (baselines).
**Steps:** 1. `--scale` parameter multiplying the seed through services (may need a fast-path flag that still hits invariants — document any shortcut). 2. Run budgets + explain_hot at scale; commit the at-scale baselines. 3. Fix top offenders (indexes, pagination) up to the session boundary; file the rest as appended tasks.
**Affected files:** seed command, baselines, offending repositories/indexes.
**Acceptance criteria:** all D2.P2.T1 budget tests green at scale-50; list endpoints paginate (no unbounded queries anywhere — grep-verifiable).
**Testing:** budget suite against the scaled DB.
**DoD:** gates green, status flipped.

## Phase D8.P3 — Reporting read models (owner: plan 05, re-anchored)

### D8.P3.T1 — Re-anchor & execute reports/BI plan 05
**Status:** todo · **Model:** Opus (design) then Sonnet
**Objective:** execute `05-reports-and-bi.md` on today's architecture: report read-model layer (denormalized, rebuildable projections for P&L, balance sheet, aging, inventory valuation, VAT), each report = one documented decision it informs (no dashboard theater — ARP_STRATEGY §5.3).
**Rationale:** reports over raw ledger joins won't survive D8.P2.T2 volumes; the month-close flagship approves cards built on these numbers.
**Prerequisites:** D1.P2.T1 (costing feeds valuation), D8.P1.T1. Read plan 05 first; it owns the report list.
**Steps:** 1. Read plan 05; split at its checkpoints into sessions. 2. Projection pattern: rebuild command + incremental update via domain events (D2.P1.T3 outbox when landed; direct-call until then). 3. Reconciliation tests: every projection total == source-of-truth query (the golden cross-check). 4. Web report pages per plan 05 with drill-to-document links (§3 mechanic 4: every number verifiable by click).
**Architecture decisions:** projections are disposable (rebuild command is the contract); no separate analytics DB until cloud phase.
**Affected files:** per plan 05 + `erp/accounting/services/projections/` (new), rebuild command, report api + web pages, locales, tests.
**Acceptance criteria:** plan 05 acceptance + reconciliation tests green at scale-50; every report page names its decision in the header description.
**Testing:** projection reconciliation suite + golden scenarios still green + web gates.
**DoD:** gates + checklist; plan 05 renamed `_done`; status flipped.
