# ARP Roadmap — Build & Remove Execution Plan

> Companion to [`Docs/ARP_STRATEGY.md`](../ARP_STRATEGY.md) (the *what and why*; this file is the
> *when and how*). Phase-level on purpose: each phase gets its own ag-plan session-file folder
> (like `ai-workspace-plan/`) **only when its turn comes** — detailed session files written months
> ahead go stale. One phase = one plan folder = one branch. Status column is updated here as
> phases land. Created 2026-07-02. **Deep-vision companion adopted 2026-07-07:**
> [`../ARP_DEEP_VISION.md`](../ARP_DEEP_VISION.md) (agentic-OS layers L0–L6, five moats, six
> founder guarantees G1–G6) — phases W+ / A2 / B2 below come from it; its guarantees bind every
> phase's acceptance.

---

## Sequencing logic

Customers before flagship: the migration agent (A) gets real companies with real data into the
product; the month-close (B) is only provable on real books. Proactive layer (C) rides on B's
report tools. WhatsApp (E) is high-wow but carries a new-dependency decision and real API cost —
it follows, not leads. Cloud (F) is a platform investment timed to demand, not enthusiasm.

## Phase 0 — Standing decisions (no build; do now)

| Item | Action | Status |
|---|---|---|
| ARP adopted (internal) | DECISIONS entry + Brief §1/§13/§17 + Identity §6 term | done 2026-07-02 |
| Cloud-default direction | DECISIONS entry (customer-hosted → deployment option) | done 2026-07-02 |
| Scope freeze | No HR / manufacturing / projects until money loop unbeatable (STRATEGY §5) | standing |
| Claims gate | No public "ARP" until a flagship flow runs live | standing |

## Prerequisite — AI Workspace (in flight)

`Docs/plan/ai-workspace-plan/` sessions 01–15: conversations, streaming, context envelope, panel,
threads, messages, attachments, tool catalog, agent loop, safe actions, page context, **guided
detours + resume**, file import, acceptance. Everything below assumes it merged. The sessions
12–13 detour demo (scanned PO → missing supplier → create → auto-resume) is **claims-gate demo
candidate #1**.

## Prerequisite — UI craft programs (in flight, queue 3–4)

The Linear-grade surface every phase demos on. Two plan folders, run in queue order
(`EXECUTION_ORDER.md`):
- `Docs/plan/linear-polish-plan/` (queue 3, FILE_01–11 done) — undo, keyboard, peek, views,
  inbox, Arabic craft, digests, ⌘K↔AI bridge, acceptance.
- `Docs/plan/unified-ui-plan/` (queue 4, created 2026-07-05) — sticky page header bar
  (‹ › history + breadcrumb + one primary + ⋯), unified print/export/share on every page
  (permission-gated, palette-registered), every table on the sales>orders selection kit
  (bulk verbs via existing endpoints only), Linear-style meta columns on real data (lifecycle
  status rings, owner initials chips, priority bars where the queue is worked by urgency,
  overdue markers on money docs). Frontend-only. Deliberate follow-ups filed, NOT in it:
  attachments (invoice photo/memo upload), photo avatars, public share links; ⋯ import entries
  arrive with Phase A's engine.

## Phase W+ — Agentic OS foundations (adopted 2026-07-07; after ai-workspace 15, before Phase A)

- **Goal:** the three OS layers everything after rides on (deep vision §2, L0–L2):
  **Action Graph v2** — every tool/action declares `requires` / `effects` / `invariants` /
  `compensation` / `risk` / `idempotency_key`, plus the contract-decorator auto-registry;
  **Verifier packs** — deterministic invariant checks after every agent write, auto-compensate on
  failure; **Simulation** — dry-run any plan in a rolled-back transaction → one diff card.
  Eval harness (`erp/assistant/evals/`, golden suite ar+en) lands here as a standing gate (G3/G4).
- **Why before A:** smart-import preview and month-close preview both ride on simulation —
  bespoke previews built first would be thrown away.
- **Unbeatable claim:** "See tomorrow's books before you post them."
- **When reached:** `Docs/plan/os-foundations-plan/` (~4–5 sessions).
- **Status:** adopted, not started (queue position 6 in `EXECUTION_ORDER.md`).

## Phase A — Migration agent ("Excel-chaos onboarding") → **Smart Import Engine**

- **Goal:** dump your spreadsheets → running company in one afternoon: masters, opening balances,
  and historical documents — detected, mapped (ar/en/mixed headers), cleaned, deduplicated,
  validated, previewed as real Conductor documents, imported through module write-paths with
  rollback, background processing, and a full report. Missing masters auto-PROPOSED and created
  on one approval. Balanced-entry validation: trial balance balances or the import proposes the
  correcting entry.
- **Plan (expanded 2026-07-04):** `Docs/plan/smart-import-plan/` — 17 sessions, new `erp/imports`
  app + adapter registry (core engine module-agnostic; each module registers an adapter).
  Queue position 6 in `EXECUTION_ORDER.md`. The conversational migration agent becomes a thin
  layer over this engine (scoped after acceptance if still wanted).
- **Builds on:** ai-workspace session 14 (assistant import card stays, later delegates) +
  session 12 blocker vocabulary; module service write-paths; assistant LLM client for
  detect/map fallback (deterministic passes first).
- **Unbeatable claim:** "From spreadsheets to a running system in one afternoon."
- **Exit test:** a real SMB's actual messy files → operating company, zero consultant hours.
- **Status:** planned (smart-import-plan created; starts after queue positions 1–5).

## Phase A2 — Implementation Consultant (adopted 2026-07-07)

- **Goal:** the AI as the implementation consultant (deep vision §3): conversational Arabic-first
  interview (one question at a time, G1) → **Egyptian industry blueprint packs** (trading,
  pharma, food, building materials, services — each = chart of accounts + VAT config + units +
  document sequences + approval chains + roles; packs are versioned data, growing per
  implementation) → simulated setup as ONE diff card → one approval → configured company.
  **Go-live readiness score** derived from the Action Graph (unmet `requires`, never-run flows);
  the Implementation Coach agent owns it until go-live.
- **Builds on:** Phase W+ (graph + simulation) + Phase A (migration fills the data half).
- **Unbeatable claim:** "Fifteen questions in Arabic → a running company. Zero consultant hours."
- **Exit test:** a non-technical founder configures a real company **unaided** (the G1 test).
- **When reached:** `Docs/plan/consultant-plan/` (~4–5 sessions).

## Phase B — Autonomous month-close (the flagship)

- **Goal:** the closing agent — reconcile, depreciation run, accrual checklist, VAT return draft,
  anomaly sweep → ONE summary card the accountant approves. Human approves the close; the system
  does the close.
- **Builds on:** agent loop + safe actions; existing depreciation run, bank recon, VAT return,
  trial balance modules — orchestrated, not rebuilt.
- **Unbeatable claim:** **"Closed by construction."** Month-close in an hour, not a week.
- **Exit test:** a real customer closes a real month start-to-finish through the agent, audit
  trail complete. **This unlocks the public ARP claim.**
- **When reached:** `Docs/plan/month-close-plan/` (~6–8 sessions).

## Phase B2 — Company Brain + Autonomy Ladder (adopted 2026-07-07)

- **Goal:** the two learning layers (deep vision L4+L5). **Company Brain:** per-tenant typed
  memory — alias table (learned from corrections), correction log (every human edit of an AI
  draft becomes few-shot context), policy memory ("wholesale = 14-day terms", stated once in
  chat, confirmed, then enforced in proposals — G6), pattern memory. Strictly per-tenant.
  **Autonomy Ladder:** per-(user,action) trust levels 0–4, earned by approval streaks, demoted
  on any correction; `post`/`destructive` never exceed level 1 without a founder-level policy
  switch; every level change audited.
- **Why after B:** needs real usage data from A/B customers to learn from; B's flagship earns
  the trust the ladder spends.
- **Unbeatable claim:** "Knows your company like a senior employee — and earns autonomy like one."
- **When reached:** `Docs/plan/brain-autonomy-plan/` (~4–5 sessions).

## Phase C — Proactive layer → **Agent Runtime + roster** (re-chartered 2026-07-07)

- **Goal:** the background workforce (deep vision L6): scheduler + **agent charters as config
  records** (scope = allowed tools, budget = tokens/day + max writes/run, cadence, escalation
  target, KPI) + **agent inbox** (evidence-linked cards; one-tap "fix it" runs a simulated plan;
  dismiss-with-reason feeds the Brain). Roster here: Auditor, Stock Controller, Collector, Cash
  Forecaster, Compliance (Bookkeeper lands with B, Coach with A2, Data Janitor with A). The
  **daily brief is the digest of agent findings** — cash, receivables, approvals, one anomaly,
  each deep-linked and evidenced.
- **Builds on:** tool catalog (read tools ARE the data source) + Phase W+ simulation (one-tap
  fixes) + a scheduled runner (scheduling decision: management command + cron vs. a worker —
  DECISIONS entry at phase start).
- **Unbeatable claim:** "Your business briefs you — not the other way around."
- **When reached:** `Docs/plan/proactive-plan/` (~4–5 sessions).

## Phase D — Bank statement reconciliation by photo/PDF

- **Goal:** photo/PDF of a bank statement → extracted lines → auto-matched against the ledger →
  unmatched lines become guided detours. No bank API dependency.
- **Builds on:** extraction pipeline (vision) + existing bank-reconciliation module + session-12
  suggestions.
- **Unbeatable claim:** "Reconcile your bank in minutes — no bank integration required."
- **When reached:** `Docs/plan/bank-vision-plan/` (~3–4 sessions).

## Phase E — WhatsApp interface

- **Goal:** company WhatsApp number: invoice photo → posted draft + reply with link; Arabic
  (Egyptian) voice note question → assistant answer; daily brief delivery. Same agent, same
  permissions (phone number ↔ user mapping, explicit enrollment).
- **Gate:** WhatsApp Business API = new dependency + per-message cost + webhook infrastructure —
  **written DECISIONS entry before any code** (STRATEGY rule 7). Voice = STT decision (provider
  vs. self-hosted) — same discipline.
- **Unbeatable claim:** "Run your company from WhatsApp."
- **When reached:** `Docs/plan/whatsapp-plan/` (~5–6 sessions).

## Phase F — Distribution platform (accountant portal + cloud)

- **Goal:** (1) accountant portal — one login, many client companies, per-client permissions;
  external accountants become the sales force. (2) Cloud multi-tenant default offering
  (schema-per-tenant groundwork exists in the master plan's session 06), self-hosted becomes
  premium. (3) **Playbook/blueprint sharing** across an accountant's clients + **anonymized
  benchmark opt-in** ("your margin vs. sector") — network effects on deep-vision moats #2/#4
  (added 2026-07-07).
- **Builds on:** identity/RBAC; the old master-plan SaaS + billing sessions fold into this phase.
- **When reached:** `Docs/plan/platform-plan/` (sized then; largest phase).

## Remove / refuse track (continuous — not a phase)

| Item | Action | Enforced by |
|---|---|---|
| HR / manufacturing / projects | Not built; requests → backlog with customer evidence | STRATEGY §5.1, rule 5 |
| Settings sprawl | Each new setting justified in PR vs. an opinionated default | rule 5 + review |
| Dashboard theater | New chart/KPI names the decision it informs, in the PR | rule 5 + review |
| "Customer-hosted" as lead prop | Brief §8.5 revised when Phase F lands | Phase F exit |
| Feature-grid marketing | Banned; comparisons argue experience + ARP test | rule 6 |

## Phase → claim → demo map (for YC / launch storytelling)

| Phase | The sentence it buys |
|---|---|
| Workspace 12–13 | "Watch it fix its own blockers and resume." |
| W+ | "See tomorrow's books before you post them." |
| A | "Onboarding is an afternoon, not a quarter." |
| A2 | "Fifteen questions in Arabic → a running company." |
| B | "The books close themselves." → **public ARP claim unlocked** |
| B2 | "It knows your company like a senior employee." |
| C | "It briefs you every morning." |
| D | "Bank reconciliation from a photo." |
| E | "Your ERP answers on WhatsApp — in Arabic, by voice." |
| F | "Every accountant is a channel." |

---

*Update the Status column and phase list here as work lands; strategy changes go to
`Docs/ARP_STRATEGY.md` first.*
