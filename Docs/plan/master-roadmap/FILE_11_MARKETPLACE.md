# D11 — Marketplace & Extensibility

> **Entry gate: FOUNDER_PLAN Phase 5 (platform & ecosystem, 2030–2032) — or an explicit
> founder decision to pull it forward.** Premature platform work is the classic startup
> death; this file deliberately contains mostly charters, plus the few cheap seeds that
> must be planted earlier because retrofitting them is 10× the cost. The adapter registry
> in `erp/imports` (smart-import) and the tool catalog in `erp/assistant` are already
> extension-shaped — they are the pattern to generalize, not replace.

---

## Phase D11.P1 — Cheap seeds (do during normal work, not as a program)

### D11.P1.T1 — Extension-point inventory & doctrine
**Status:** todo · **Model:** Opus — single session
**Objective:** `Docs/patterns/extensibility.md`: catalog every seam that already behaves like an extension point (import adapters, assistant tools/contracts, webhook topics, bank profiles, industry blueprint packs from A2, report projections) + the doctrine: new seams follow the registry pattern (typed registration, versioned interface, no monkey-patching), and NOTHING is promised publicly.
**Rationale:** when Phase 5 arrives, the platform is assembled from seams that stayed clean — this doc keeps them clean for four years at near-zero cost.
**Prerequisites:** smart-import queue 8 merged (adapter registry exists as the exemplar).
**Steps:** 1. codegraph inventory of registry-shaped seams. 2. Write doctrine + per-seam stability notes (internal/frozen/candidate-public). 3. Link from ARCHITECTURE.md.
**Affected files:** doctrine doc (new), ARCHITECTURE.md.
**Acceptance criteria:** every listed seam has an owner file, interface sketch, and stability label.
**Testing:** n/a.
**DoD:** committed, status flipped.

### D11.P1.T2 — Stable-ID discipline
**Status:** todo · **Model:** Haiku
**Objective:** verify every externally-visible identifier (permission codes, event topic names, error codes, API v1 field names, tool names) has a stated stability rule in its pattern doc; add a one-line "renaming any of these is a breaking change requiring a DECISIONS entry" rule to CONTRIBUTING.
**Rationale:** ecosystems die on renamed identifiers; the rule costs one line today.
**Prerequisites:** D4.P1 docs exist.
**Steps:** audit the five identifier classes; add missing stability notes; CONTRIBUTING line.
**Affected files:** pattern docs, CONTRIBUTING.
**Acceptance criteria:** all five classes covered in writing.
**Testing:** n/a.
**DoD:** committed, status flipped.

## Phase D11.P2 — Platform program (charter only until Phase 5 gate)

### D11.P2.T1 — Platform charter
**Status:** todo (gated) · **Model:** Opus
**Objective:** when the gate opens: DECISIONS-backed charter choosing the extension model — server-side sandboxed apps vs API/webhook-only partners vs both — plus SDK language, review policy, revenue share, and the isolation/security architecture (extensions NEVER bypass RBAC/audit; they act as installed-per-tenant API clients with scoped tokens from D9.P1.T1).
**Rationale:** the single most security-sensitive architectural choice after tenancy; chartered, argued, founder-signed before any code.
**Prerequisites:** D2.P3 complete (tenancy), D9 complete (API v1 + webhooks stable ≥1 year), FOUNDER_PLAN Phase 5 entry gate.
**Steps:** full charter session against the then-current facts; spawn `marketplace-plan/` folder via ag-plan.
**Affected files:** DECISIONS, new plan folder.
**Acceptance criteria:** charter answers isolation, distribution, review, billing, and support questions with named owners.
**Testing:** n/a.
**DoD:** founder-signed charter committed.
