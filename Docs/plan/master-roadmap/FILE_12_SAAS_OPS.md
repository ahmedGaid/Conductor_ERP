# D12 — Product & SaaS Operations

> Entry gate: D2.P3 tenancy decision + FOUNDER_PLAN Phase 3 (SaaS machine, 2028–2029).
> Legacy specs `06-saas-multitenancy.md` (absorbed by D2.P3) and
> `07-billing-and-provisioning.md` (re-anchored here) are the raw material. Pricing page
> draft already exists (`conductor_pricing (3).html` in repo root — untracked; fold into
> marketing when this phase starts). Cloud infra itself (hosting, orchestration) gets its
> own plan folder at Phase F via ag-plan — this file owns the PRODUCT side of SaaS.

---

## Phase D12.P1 — Plans & entitlements

### D12.P1.T1 — Entitlement model
**Status:** todo (gated on D2.P3.T2) · **Model:** Opus (design) then Sonnet
**Objective:** per-tenant plan record (plan code, seats, module set, AI-usage allowance, valid-until) + a single `entitled(tenant, capability)` check service + enforcement at the SAME choke-points as RBAC (never scattered `if plan ==` conditionals); over-limit behavior is designed (blame-free explain + upgrade path), never a hard wall mid-task.
**Rationale:** billing without entitlements is unenforceable; entitlements bolted on late means a conditional in every view.
**Prerequisites:** D2.P3.T2 (tenant context), founder-approved plan matrix (BLOCKER until priced).
**Steps:** 1. Founder session: plan matrix v1 (start: Solo / Team / Premium-self-hosted) recorded in DECISIONS. 2. Model + service in `erp/core` beside tenancy. 3. Enforcement at permission-check choke-point + AI-call entry. 4. Designed over-limit states (ar/en). 5. Admin (us) override tooling with audit.
**Architecture decisions:** capabilities are coarse (module/seat/AI-quota), never per-button; grace behavior default-on (7 days) — calm brand extends to billing.
**Affected files:** `erp/core/` entitlements (new), choke-point integrations, web upgrade-path states, locales, tests.
**Acceptance criteria:** seat N+1 invite blocked with designed state; expired plan enters read-only-with-grace mode, nothing deleted.
**Testing:** pytest entitlement matrix; web gates.
**DoD:** gates + checklist, status flipped.

### D12.P1.T2 — Usage metering (AI + seats)
**Status:** todo (gated) · **Model:** Sonnet
**Objective:** per-tenant counters: AI tokens/calls (hooked at the one LLM client — `erp/assistant/client.py`), active seats, document volume; daily rollups; internal admin view + the customer-visible usage page (transparency = trust).
**Rationale:** AI-usage revenue layer (FOUNDER_PLAN §10) needs metering months before billing does; also the cost-control input for ai-reliability's budget work — coordinate, don't duplicate its gateway counters (queue 6 FILE_02): if the gateway lands first, this task consumes ITS counters.
**Prerequisites:** D12.P1.T1; check ai-reliability FILE_02 status first.
**Steps:** 1. Counter writes at client entry (or gateway consumption). 2. Rollup command + retention. 3. Customer usage page with plain-words explanation of what counts; admin cross-tenant view.
**Architecture decisions:** meter in integers (tokens, calls, piasters of cost), rollup daily, raw events pruned per D8.P2.T1 policy.
**Affected files:** assistant client or gateway hook, rollup model+command, web usage page, locales, tests.
**Acceptance criteria:** seeded AI calls appear in tenant rollups and on the customer page; numbers reconcile counter-vs-rollup.
**Testing:** pytest metering + rollup reconciliation.
**DoD:** gates + checklist, status flipped.

## Phase D12.P2 — Billing & lifecycle (re-anchors legacy plan 07)

### D12.P2.T1 — Subscription billing integration
**Status:** todo (gated) · **Model:** Opus
**Objective:** execute plan 07's billing half on today's stack: subscription records synced with the chosen payment rail (D9.P3.T2 decision), invoice-the-customer flow (we dog-food our own invoicing), dunning with calm designed comms, entitlement sync on payment events.
**Rationale:** revenue collection is the SaaS machine's heart; plan 07 wrote the shape, the rail decision makes it concrete.
**Prerequisites:** D12.P1.T1/T2, D9.P3.T2 decided, D9.P2.T1 (webhooks pattern for inbound payment events).
**Steps:** re-anchor plan 07 against current code; split at its checkpoints; inbound payment webhooks verified + idempotent; every entitlement change audited.
**Architecture decisions:** we bill through OUR sales module (our invoice = the artifact) with the rail as payment method — the ultimate dog-food.
**Affected files:** per re-anchored plan 07 + `erp/pricing`/billing app placement per ARCHITECTURE.
**Acceptance criteria:** sandbox end-to-end: subscribe → pay → entitled → fail-payment → dunning → grace → suspended, all states designed + audited.
**Testing:** pytest with rail sandbox mocks; manual sandbox run recorded.
**DoD:** gates + checklist, plan 07 `_done`, status flipped.

### D12.P2.T2 — Tenant lifecycle operations
**Status:** todo (gated) · **Model:** Sonnet
**Objective:** operational tooling: tenant provision (self-serve signup → company created + seeded defaults), suspend/resume, export-all-data (the trust promise: leave anytime with your books — full export in open formats), delete-after-retention; each one command + admin UI action + audit + runbook.
**Rationale:** SaaS ops without lifecycle tooling = founder doing SQL surgery on production; the export promise is brand-critical (blame-free even when leaving).
**Prerequisites:** D12.P2.T1, D8.P2.T1 (retention policy).
**Steps:** 1. Provision service reusing seed/setup paths. 2. Suspend = entitlement state, data untouched. 3. Export: per-tenant dump (CSV per document type + attachments zip) via background task, download link notified. 4. Deletion honors retention + produces a certificate record.
**Architecture decisions:** export is a product feature, not an ops favor — designed UI, both languages.
**Affected files:** lifecycle services/commands, admin UI, customer export page, locales, runbook, tests.
**Acceptance criteria:** full cycle on a test tenant: provision → use → suspend → resume → export (opens in Excel, Arabic intact — UTF-8 BOM) → delete after policy.
**Testing:** pytest lifecycle suite; manual export file check in Excel.
**DoD:** gates + checklist, status flipped.

## Phase D12.P3 — Operating the service

### D12.P3.T1 — Status page + uptime discipline
**Status:** todo (gated on cloud launch) · **Model:** Sonnet
**Objective:** public status page (static, self-hosted, no third-party) fed by our own uptime checks against `/readyz`, incident posts written per the incident runbook's templates; internal alerting to founder phone via the notifications app.
**Rationale:** trust brand demands honesty when down; a status page written during an outage is too late.
**Prerequisites:** D7.P3.T3, D5.P3.T2, cloud deployment live.
**Steps:** checker command (runs from a second location), static page generator, alert wiring, incident-post workflow doc.
**Affected files:** checker + generator scripts, notifications wiring, runbook link.
**Acceptance criteria:** simulated outage → founder alerted <5 min → status page shows incident.
**Testing:** the simulation.
**DoD:** simulation recorded, status flipped.
