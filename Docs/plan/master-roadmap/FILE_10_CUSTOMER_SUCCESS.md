# D10 — Customer Implementation & Success

> Existing owners (do NOT duplicate): zero-prep migration → `smart-import-plan/` (queue 8);
> AI implementation consultant + go-live readiness score → arp Phase A2 (`consultant-plan/`
> when reached); in-app help exists at `apps/web/src/help/`. This domain adds the human-scale
> success loop around those: onboarding visibility, feedback capture, support discipline,
> and customer health — sized for the first 10→100 customers (FOUNDER_PLAN Phases 1–2).

---

## Phase D10.P1 — Onboarding visibility

### D10.P1.T1 — In-app setup checklist
**Status:** todo · **Model:** Sonnet
**Objective:** a designed "getting started" surface for a fresh company: derived (not stored) checklist — company profile done, chart of accounts confirmed, opening balances posted, first product/partner/invoice created, users invited — each item deep-links to the action and disappears when done; whole surface disappears when complete.
**Rationale:** the founder currently walks every new company through setup personally; this is the self-serve floor until A2's consultant lands (which supersedes parts of it — build accordingly thin).
**Prerequisites:** D1.P1.T4 (opening balances is a checklist item). Check A2 charter first: this checklist must be derivable from the same signals A2's readiness score will use — share the derivation service.
**Steps:** 1. `erp/setup/services/readiness.py`: pure derivation returning item list + done flags from real data. 2. API + web card on the home/dashboard route, dismissible per-user, auto-hides at 100%. 3. Arabic-first copy through the lexicon; celebratory-but-quiet completion state (no confetti — settled motion).
**Architecture decisions:** derived state only (no checklist table to drift); service is the shared base for A2's score.
**Affected files:** `erp/setup/services/readiness.py` (new), api, web home card, locales, tests.
**Acceptance criteria:** fresh seedless company shows all items; completing each (via real actions) removes it; complete company shows nothing.
**Testing:** pytest derivation matrix; E2E addition to smoke pack if D6.P2.T1 landed.
**DoD:** gates + checklist, status flipped.

### D10.P1.T2 — Guided first-invoice moment
**Status:** todo · **Model:** Sonnet
**Objective:** the first successful posted invoice for a company triggers a one-time designed moment: confirmation of what just happened (posted, numbered, VAT-correct, in the ledger — with drill links) — the "trust is visible" beat.
**Rationale:** the product's core promise (correct money) must be FELT at the first real action; retention starts here.
**Prerequisites:** D10.P1.T1.
**Steps:** 1. First-post detection in the derivation service. 2. One-time dismissible panel on the invoice success state showing the four facts with links (journal entry, sequence, VAT line). 3. Copy per brand voice, both languages.
**Architecture decisions:** reuses the readiness derivation; never repeats; no modal hijack (inline panel).
**Affected files:** readiness service, invoice page success state, locales.
**Acceptance criteria:** appears exactly once per company on first posted invoice; all four links resolve.
**Testing:** pytest detection; manual walk of the moment in both languages.
**DoD:** gates + checklist, status flipped.

## Phase D10.P2 — Feedback & support loop

### D10.P2.T1 — In-app feedback capture
**Status:** todo · **Model:** Sonnet
**Objective:** a quiet feedback affordance (⋯ menu + palette entry): category (bug/idea/confusion), free text, auto-attached context (route, app version, user role — shown to the user before send, nothing hidden), stored in a `feedback` table + notification to admin; NO external service.
**Rationale:** Phase 1–2 learning depends on friction reports from the first 10 customers; email/WhatsApp fragments get lost.
**Prerequisites:** none.
**Steps:** 1. Model in `erp/core` (or `erp/crm` if ARCHITECTURE placement says so). 2. API + palette-registered action + ⋯ entry per unified-ui conventions. 3. Admin list view with status (new/seen/done) and designed states. 4. Blame-free microcopy; transparency line listing attached context.
**Architecture decisions:** internal only; export to any tracker is a later decision.
**Affected files:** model+migration, api, web dialog + admin page, locales, tests.
**Acceptance criteria:** feedback submitted from any page lands with correct context; admin can mark states.
**Testing:** pytest + web gates.
**DoD:** gates + checklist, status flipped.

### D10.P2.T2 — Support runbook + SLA statement
**Status:** todo · **Model:** Haiku
**Objective:** `Docs/runbooks/support.md`: intake channels (WhatsApp business line, feedback table, email), triage severities with response targets (S1 system-down: 2h response; S2 money-wrong: same-day; S3 friction: 72h), escalation to founder, and the weekly feedback-review ritual; plus the customer-facing SLA paragraph (ar+en) for contracts.
**Rationale:** support promises made ad-hoc become liabilities; a written floor scales to the first hire.
**Prerequisites:** D10.P2.T1.
**Steps:** write it; founder confirms the targets are keepable solo.
**Affected files:** runbook (new).
**Acceptance criteria:** founder sign-off; SLA paragraph exists in both languages.
**Testing:** n/a.
**DoD:** committed, status flipped.

## Phase D10.P3 — Customer health (entry gate: ≥10 live companies)

### D10.P3.T1 — Usage health signals
**Status:** todo · **Model:** Sonnet
**Objective:** per-company weekly health derivation: documents posted trend, active users, last-login recency, feature breadth (modules touched), error rate — one internal admin page ranking companies by risk, each risk factor stated in words (no dashboard theater: the decision it informs = "who do I call this week").
**Rationale:** churn at 10–100 customers is silent; the founder needs the call list, not charts.
**Prerequisites:** D7.P3.T3 (logs), live customers.
**Steps:** 1. Derivation service over existing data (audit trail + documents) — no new event tracking. 2. Internal page (admin permission) with the ranked list + word-labeled factors + designed states. 3. Weekly digest into notifications.
**Architecture decisions:** derived from operational data only; no third-party analytics (privacy story stays clean).
**Affected files:** `erp/monitoring/` or `erp/crm/` service per placement rule, api, admin page, locales, tests.
**Acceptance criteria:** seeded scenarios rank plausibly (dormant company tops risk); every factor readable as a sentence.
**Testing:** pytest derivation matrix; web gates.
**DoD:** gates + checklist, status flipped.
