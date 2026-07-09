# D9 — Integrations & APIs

> Existing owners: ETA e-invoicing → `09-eta-integration.md` (tracked as D1.P3.T1 — tax is
> core, not integration); WhatsApp → arp Phase E (decision-gated, own plan folder when
> reached). This domain builds the public API surface, webhooks, and the import/export
> edges — the plumbing Phase 5 (platform/ecosystem, FOUNDER_PLAN) later rides on.

---

## Phase D9.P1 — Public API v1 foundation

### D9.P1.T1 — API auth: personal access tokens
**Status:** todo · **Model:** Sonnet
**Objective:** scoped API tokens: user-created, named, permission-subset-of-owner, hashed at rest, revocable, `last_used_at` tracked, all usage audited as the owning user (never a system actor — §3 mechanic 1 applies to API clients too).
**Rationale:** accountant portal, integrations, and customer scripts all need non-session auth; tokens scoped-below-owner keep RBAC true.
**Prerequisites:** D5.P1.T1 (auth hardening first), D5.P2.T3 (rate limits wrap tokens).
**Steps:** 1. Token model in `erp/identity` (prefix+hash storage, scope list referencing existing permission codes). 2. Auth backend accepting `Authorization: Bearer` beside session auth. 3. Management UI page under settings: create (secret shown once, designed state), list, revoke. 4. Audit + rate-limit integration. 5. Docs stub for D13.
**Architecture decisions:** tokens are permission-subsets (cannot exceed owner); no OAuth server yet (DECISION-GATED at marketplace phase).
**Affected files:** `erp/identity/` (model, backend, api), migration, web settings page, locales, tests.
**Acceptance criteria:** token with read-only scope can list invoices, cannot post one (403 envelope error); revoked token 401s; owner's audit trail shows token-attributed actions.
**Testing:** `pytest erp/identity -k token`; manual curl round-trip documented in the PR.
**DoD:** gates + checklist, status flipped.

### D9.P1.T2 — API v1 surface + versioning contract
**Status:** todo · **Model:** Opus (contract) then Sonnet
**Objective:** declare `/api/v1/` as the stable external surface over the EXISTING internal endpoints (thin, explicitly listed re-exports — masters + documents read, document draft-create for sales/purchasing), with a written versioning/deprecation policy (v1 never breaks; additive only; 6-month deprecation floor).
**Rationale:** integrations built on internal endpoints break silently; a small stable surface beats a big unstable one. This is the platform seed.
**Prerequisites:** D9.P1.T1, D4.P1.T3 (error envelope is part of the contract), D4.P2.T3 (types/OpenAPI source).
**Steps:** 1. Choose the v1 endpoint list (start ≤15 endpoints) with founder sign-off. 2. URL layer `erp/api/v1/` mapping to internal serializers marked stable (fields listed explicitly, never `__all__`). 3. Version policy doc `Docs/patterns/api-versioning.md`. 4. Contract tests freezing response shapes (golden JSON fixtures).
**Architecture decisions:** v1 = curated allowlist, internal API remains free to move; draft-create only, posting stays in-app (human-in-the-loop preserved for external writers too).
**Affected files:** `erp/api/` app or `erp/core` urls module (per ARCHITECTURE.md placement rule), policy doc, contract tests, locales n/a.
**Acceptance criteria:** all v1 endpoints respond under token auth with frozen shapes; contract test fails on any field removal/rename.
**Testing:** contract test suite; full pytest.
**DoD:** gates green, status flipped.

## Phase D9.P2 — Webhooks (needs D2.P1.T3 outbox implemented)

### D9.P2.T1 — Outbound webhooks
**Status:** todo · **Model:** Sonnet
**Objective:** tenant-configurable webhook subscriptions (event allowlist: document posted, payment received, master created/archived), HMAC-signed payloads, at-least-once via the outbox deliverer, exponential retry with dead-letter + notification, delivery log UI.
**Rationale:** the cheapest integration surface for customers' existing tools; also the ecosystem primitive partners will build on.
**Prerequisites:** D2.P1.T3 outbox IMPLEMENTED (its appended task), D9.P1.T2, D5.P2.T2 (secret handling for signing keys).
**Steps:** 1. Subscription model + signing secret (rotatable). 2. Deliverer consumes outbox topics → HTTP POST with `X-Signature` HMAC-SHA256, timeout 10s, retries 5 with backoff, then dead-letter + notify subscriber-owner. 3. SSRF guard: destination URL validated against private-network denylist (reuse/extend plan-00's SSRF utilities). 4. Settings UI: subscription CRUD + delivery log with designed states. 5. Docs stub.
**Architecture decisions:** payloads carry ids + minimal snapshot, consumer re-fetches via API v1 (avoids stale-data disputes); signatures mandatory, no unsigned mode.
**Affected files:** `erp/core/` or dedicated `erp/webhooks/` per ARCHITECTURE placement, migration, deliverer command, web settings pages, locales, tests with a local receiver fixture.
**Acceptance criteria:** posted invoice triggers signed delivery to the test receiver; unreachable receiver dead-letters after 5 attempts and notifies; private-IP destination rejected at save time.
**Testing:** pytest with threaded local HTTP receiver; signature verification test vector committed.
**DoD:** gates + checklist, status flipped.

## Phase D9.P3 — Edge integrations (each DECISION-GATED)

### D9.P3.T1 — Bank statement file import (CSV/OFX-ish)
**Status:** todo · **Model:** Sonnet
**Objective:** statement file upload → parsed lines into the existing bank reconciliation module's matching flow; Egyptian bank CSV quirks handled by per-bank profile configs (data, not code).
**Rationale:** stepping stone to the vision "recon by photo/PDF" (arp build item 5) — file-based lands value now with zero new deps.
**Prerequisites:** D5.P2.T4 (upload validation); existing recon module (verify via codegraph).
**Steps:** 1. Parser service with bank-profile registry (delimiter, date format, column map — JSON per bank, seeded with 2 real formats from the founder). 2. Wire into recon matching. 3. Import UI on the recon page (reuse import primitives from smart-import when queue 8 lands — if this task runs first, keep the UI minimal and note the handoff).
**Architecture decisions:** profiles are data; unknown format → actionable error asking for a sample, never a crash.
**Affected files:** `erp/accounting/services/bank_import.py` (new), profile fixtures, recon api/page, locales, tests with fixture files.
**Acceptance criteria:** two real-format fixtures import and match; malformed file → designed error.
**Testing:** pytest with fixture statements; web gates.
**DoD:** gates + checklist, status flipped.

### D9.P3.T2 — Payment gateway decision (charter only)
**Status:** todo · **Model:** Opus
**Objective:** DECISIONS entry: which Egyptian payment rail (Paymob/Fawry/instapay-adjacent) for SaaS billing (D12) and/or customer invoice payment links, or explicit deferral with the trigger condition.
**Rationale:** new dependency + money movement = maximum decision weight; write it before anyone codes.
**Prerequisites:** FOUNDER_PLAN Phase 2 entry (paying customers exist).
**Steps:** comparison against OUR needs (SaaS billing first; invoice links second), fees, settlement, API quality; founder decides.
**Affected files:** DECISIONS.
**Acceptance criteria:** entry with choice/deferral + trigger + integration task appended here when chosen.
**Testing:** n/a.
**DoD:** entry committed, status flipped.
