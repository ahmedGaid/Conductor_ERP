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

## Craft doctrine (binding lens on every phase — adopted 2026-07-18)

Conductor does not try to out-feature Odoo; it wins on **craft** — faster, calmer, smarter, more
trustworthy, more beautiful, not bigger (the "Linear + Apple + Notion of ERP" bar). So every phase's
acceptance also binds to **The Conductor Standard** (the 8-point ship test in the
[Product Design & Engineering Directive](../Brand/Conductor_ERP_Product_Design_Engineering_Directive.md))
and the Apple-lesson craft thesis (Brief §2): *we compete on the feeling of using the software.* A
phase is not done when its function works — it's done when it *feels* Conductor. Positioning room
this buys (internal, same claims-gate discipline): Conductor as the **Calm Company Operating
System** — the owner conducts; the system quietly coordinates the details — broader than "ERP",
letting the agentic layers (deep-vision L0–L6) grow under one identity.

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
  arrive with Phase A's engine. unified-ui-plan closed 2026-07-09 (FILE_09 acceptance, both
  languages, gates + brand-feel green); the three deferred items get their own one-paragraph stub
  below so they don't get lost before someone schedules them:
  - **Attachments** — invoice photo / memo image on sales, purchasing and accounting documents.
    Needs an upload API (multipart or presigned URL), a storage decision (local disk vs. object
    storage — customer-hosted single-tenant, so likely local disk under a per-org path unless a
    customer needs S3-compatible), a gallery/lightbox component in the app's own visual language,
    and a DocumentMenu "Attach file" verb. No plan file yet — needs its own `FILE_00` scoping pass
    before it's queue-ready.
  - **Photo avatars** — replace `OwnerChip`'s monochrome initials with an uploaded photo where one
    exists, falling back to initials otherwise. Rides on the same upload/storage decision as
    attachments above — do them together, not separately, once that decision is made.
  - **Smart-import ⋯ entry points** — once `smart-import-plan`'s backend engine lands (queue
    position 8, Phase A), list pages get an "Import" item in the ⋯ menu (or as the visible primary
    on empty-state lists) that opens the import wizard. The unified-ui page-actions plumbing
    (`useSetPageActions` / `useListPageActions`) already supports adding this with no new
    primitive — it's a wiring task for whichever smart-import session builds the entry UI.

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
- **Status:** **delivered** by `smart-import-plan/` (FILE_01-17, acceptance signed off 2026-07-26 —
  see DECISIONS.md). `erp/imports` app + adapter registry live for customers/suppliers/items/
  contacts, sales quotations/orders/invoices, purchase orders/invoices, journal entries, trial-
  balance opening (with correction-approval), inventory opening; detect → map → clean → dedupe →
  preview → creation-plan → execute (all four strategies, background runner with live progress/
  pause/resume/kill-recovery, verified at real 100k-row scale) → rollback → report. NOT built:
  continuous Excel sync, drag-drop mapping, AI-guessed auto-fix, PDF report, per-document ACLs,
  multi-sheet-per-upload cycling, employees/projects/assets import types (STRATEGY §5) — the
  conversational migration-agent layer over this engine stays a scoped future follow-up, not
  started.

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

## Craft & Trust polish — folded from the CPO "Master Plan" review (2026-07-18)

A founder-supplied 6-phase CPO plan was reviewed against this roadmap + `EXECUTION_ORDER.md`. ~90%
was already planned or shipped — Phase 1 (zero-friction) = linear-polish + unified-ui +
field-primitives (done); Phase 2 (Apple polish) = those + `conductor-brand`; Phase 3 "AI preview
(current→new→impact→confirm)" = the shipped **SimulationDiffCard** (Phase W+); Phase 4 (proactive
AI) = **Phase C** agent roster + daily brief; Phase 5 (luxury) = saved views (done) + ⌘K (done) +
the dashboard brief; Phase 6 (brand) = the Arabic-lexicon moat + Brief voice. Its five "top
priorities" already match this roadmap's front-loaded order (onboarding A/A2 → workflow polish →
proactive C → design system → brand language). **Not re-adopted as a parallel plan** (one source of
truth). Full verdict incl. rejected/guarded items in DECISIONS.md.

Three genuinely-new, on-brand, not-yet-queued items are queued here as stubs (off critical path,
founder-standing-OK UI/UX — `EXECUTION_ORDER.md` track **P**; scoped into a `FILE_00` when
scheduled, not pre-written months ahead):

- **System Confidence panel.** The reassurance complement to the shipped "Needs attention today"
  (which surfaces *problems*): a calm, positive health strip — e.g. *Books balanced ✓ · VAT ready ✓
  · Backups: yesterday ✓ · Stock health ✓ · Assistant connected ✓* — each colour paired with a word
  (never colour alone), each deep-linking to its proof. Pure trust UX. Frontend + light read
  endpoints.
- **Calm milestone moments.** Useful, quiet delight — first profitable month, 1000th invoice — as a
  gentle, dismissible acknowledgment. **No confetti, no sound** (that would break the quiet/calm
  brand); the *gentle-warning* side (e.g. unexpected stock-out) already belongs to Phase C agent
  findings.
- **English product-vocabulary canon.** Extend the lexicon moat (Identity System §6, today
  Arabic-first) to English product nouns: prefer human words (Assistant, Timeline, Insights,
  Workspace, the daily brief's name) over "Master Data / Utilities / Configuration" where a human
  word fits. One canonical English word per concept, registered before use; then a light rename +
  i18n pass. Brand-doc task first, build second.

**Reviewed and deliberately NOT queued** (reasons in DECISIONS.md): success/notification **sounds**
(against the quiet brand — opt-in-only if ever), **silent autosave / "Save & Continue"** on
accounting/order/journal forms (settled: explicit draft-save only — half-entered postings must not
autosave), **column resize/reorder/pinning** (already weighed and deferred as low-value — no new
evidence), and **natural-language filters** (allowed only as assistant tool-use → structured filter,
never free-text-to-SQL — a standing decision).

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
