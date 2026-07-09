# D13 — Documentation & Knowledge Management

> Continuous domain — no big program, hard-gated at each phase exit instead. Existing
> knowledge system: CLAUDE.md map + skills (erp-status/frontend/brand/history) + DECISIONS
> + plan folders + in-app help (`apps/web/src/help/`) + RAG knowledge base (queue 2 owns
> the AI-readable half). This domain fills: user-facing docs, API docs, runbook coverage,
> and the owner's mirror.

---

## Phase D13.P1 — Engineering knowledge (mostly delivered by other domains — tracked here)

### D13.P1.T1 — Docs inventory & gap gate
**Status:** todo · **Model:** Haiku
**Objective:** `Docs/INDEX.md`: every doc in `Docs/` listed with owner-domain, freshness date, and audience (engineer/agent/owner/customer); a warn-gate flags docs untouched >6 months for review and orphan docs not in the index.
**Rationale:** stale docs are worse than none — agents follow them into walls; the index makes rot visible.
**Prerequisites:** none.
**Steps:** 1. Walk `Docs/`, classify. 2. Write index. 3. `scripts/gates/gate21.py` (warn): orphans + stale entries. 4. Rule in CONTRIBUTING: new doc = index row, same commit.
**Affected files:** `Docs/INDEX.md` (new), gate, CONTRIBUTING.
**Acceptance criteria:** index complete; planted orphan flagged.
**Testing:** plant-test.
**DoD:** gates green, status flipped.

### D13.P1.T2 — Runbook coverage checklist
**Status:** todo · **Model:** Haiku
**Objective:** verify the runbook set exists and dry-runs clean: dev-setup (D7.P1.T1), release (D6.P3.T1), backup-restore (D7.P3.T2), incident (D5.P3.T2), install (D7.P3.T1), support (D10.P2.T2); missing ones filed as blockers on their owning tasks — this task only audits.
**Rationale:** runbooks scattered across domains need one completeness check before any customer-facing launch gate.
**Prerequisites:** the listed tasks (this is a phase-exit audit — run it at FOUNDER_PLAN Phase 2 entry).
**Steps:** checklist run; file gaps; add runbook list to INDEX.md.
**Affected files:** INDEX.md.
**Acceptance criteria:** all six exist with dry-run dates in their footers.
**Testing:** the audits themselves.
**DoD:** committed, status flipped.

## Phase D13.P2 — Customer-facing documentation

### D13.P2.T1 — In-app help content system audit + authoring pass
**Status:** todo · **Model:** Sonnet
**Objective:** survey `apps/web/src/help/` (how content is stored/rendered), then author/complete help articles for the money loop: first invoice, receiving payment, inventory receipt, month routines, VAT return — Arabic FIRST, English second; every article ends with "what can go wrong" (blame-free).
**Rationale:** support load (D10.P2) shrinks with every good article; Arabic-first help is a differentiator no competitor has.
**Prerequisites:** none (content rides existing system; if survey finds no real system, STOP and file a design task instead — don't improvise one).
**Steps:** 1. Survey via codegraph. 2. Article list approved by founder (start: the five above). 3. Author in the lexicon's canonical terms; screenshots from the seed company (D6.P2.T3) so they're reproducible. 4. Link articles from their pages' help affordance.
**Architecture decisions:** content lives wherever the existing system dictates; terms ONLY from Identity System §6.
**Affected files:** help content files, page help links, locales if titles are keys.
**Acceptance criteria:** five articles live in both languages, reachable from their screens; terminology audit clean (grep against lexicon).
**Testing:** parity + tsc + manual read-through of Arabic by founder.
**DoD:** gates + checklist, status flipped.

### D13.P2.T2 — API reference (rides D9)
**Status:** todo · **Model:** Sonnet
**Objective:** generated API v1 reference (from the D4.P2.T3 OpenAPI/type source): endpoints, auth, error envelope, webhook signatures, rate limits — published as a static page in the docs site or repo; versioned with the API.
**Rationale:** integrations (D9) are only as usable as their docs; generated = never stale.
**Prerequisites:** D9.P1.T2, D9.P2.T1, D4.P2.T3.
**Steps:** generation script from the OpenAPI source + hand-written guides (auth walkthrough, webhook verification sample code); wire regeneration into the API contract-test gate.
**Affected files:** `Docs/api/` (generated + guides), generation script, gate hook.
**Acceptance criteria:** reference regenerates deterministically; drift between code and published reference fails the gate.
**Testing:** plant a field change without regeneration.
**DoD:** gates green, status flipped.

## Phase D13.P3 — The owner's mirror (standing)

### D13.P3.T1 — Owner Manual freshness rule
**Status:** todo · **Model:** Haiku (recurring)
**Objective:** standing rule + mechanism: `Docs/OWNER_MANUAL.html` (the founder-facing mirror of this roadmap) is updated whenever a master-roadmap task flips status or a domain file changes — a warn-gate compares domain-file mtimes vs the manual's embedded build date.
**Rationale:** the owner's visibility must not decay into fiction; a stale manual is worse than none.
**Prerequisites:** OWNER_MANUAL.html exists (created 2026-07-08 with this roadmap).
**Steps:** 1. Embed build-date meta in the manual (done at creation). 2. Gate compares dates (warn). 3. CONTRIBUTING line: status flips include the manual touch — regenerate the progress data block.
**Affected files:** gate script, CONTRIBUTING.
**Acceptance criteria:** editing a domain file without touching the manual warns.
**Testing:** plant-test.
**DoD:** gates green, status flipped.
