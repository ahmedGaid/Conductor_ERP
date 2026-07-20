# EXECUTION ORDER — how Claude runs the plan queue

**Audience: Claude Code, at the start of any working session on this repo.**
This file is the single answer to "what do I work on and how". The `erp-status` skill points
here; deep per-task detail lives inside each plan's own FILE_NN.

---

## The queue (strict order)

| Pos | Plan | Files | Purpose |
|---|---|---|---|
| **1** | `Docs/plan/ai-workspace-plan/` | FILE_10 only | Safe actions — code already in the working tree, finish + merge it FIRST |
| **2** | `Docs/plan/rag-knowledge-plan/` | FILE_01 → FILE_11 | RAG knowledge base + source routing + harness hardening |
| **3** | `Docs/plan/linear-polish-plan/` | FILE_01 → FILE_13 | Linear-level feel: undo, keyboard, peek, views, inbox, Arabic craft, digests, ⌘K bridge |
| **4** | `Docs/plan/unified-ui-plan/` | FILE_01 → FILE_09 | Unified surface: sticky page header bar (‹ › + breadcrumb + primary + ⋯), unified print/export/share actions, all tables to the sales>orders kit, Linear-style meta columns (rings/chips/priority/due) |
| **5** | `Docs/plan/ai-workspace-plan/` | FILE_11 → FILE_15 | Page assistant, guided detours, workflow resume, file import, FINAL acceptance |
| **6** | `Docs/plan/ai-reliability-roadmap/` | FILE_01 → FILE_02 | **AI reliability foundations** (Phases 1–2 of the 24-month blueprint): traces + eval harness + golden dataset + prompt registry, then AI gateway (routing/failover/caching/budgets). Supersedes the eval-harness slice of os-foundations |
| ~~**7**~~ ✅ | `Docs/plan/os-foundations-plan/` | FILE_01 → FILE_05 **DONE (2026-07-12)** | **Phase W+ CLOSED** — Action Graph v2 (L0), verifier packs + wiring (L1), simulation engine + diff card (L2). Claim earned: "See tomorrow's books before you post them." Follow-up (unscheduled, Haiku-fit): mechanical 13-action L0 metadata fan-out. NOTE for pos 8: smart-import FILE_13 preview UI should consume `SimulationDiffCard` |
| **8** | `Docs/plan/delivery-readiness/` | FILE_05 → FILE_07 | **PRE-HANDOVER SET (added 2026-07-16) — blocks customer handover.** FILE_05 partial payments UI → FILE_06 `provision_customer` command → **then jump to pos 9 twenty-harvest FILE_01→03 (versioning + upgrade command + drill/snapshot gates — explicitly part of this set)** → **then pos 8A pre-handover-hardening (the QA-audit Phase 0 — must complete first)** → back to FILE_07 HANDOVER GATE sections C/D/E (on the real customer machine; ETA day-one + canvas human smoke + restore drill live inside it). This ordered jump is deliberate and overrides the lowest-position rule |
| **8A** | `Docs/plan/pre-handover-hardening/` | FILE_02 → FILE_06 | **★ THE QA AUDIT RECOMMENDATION (added 2026-07-18) — runs BEFORE the FILE_07 customer handover gate. Blocks handover.** FILE_01 done 2026-07-18 (founder picked Branch A, see `DECISIONS.md`). Remaining: FILE_02 CI safety net (gates+pytest+web on push/PR), FILE_03 top-level React error boundary, FILE_04 fresh gate-run artifact, FILE_05 LICENSE+support terms, FILE_06 handover loose ends (canvas smoke, partial-pay Q, delete `phase1d_qa`). Small–Medium each. Index: `FILE_00_INDEX.md` |
| **8C** | `Docs/plan/einvoice-eta-live/` | FILE_01 → FILE_05 | **CONFIRMED Must-Have handover blocker (founder picked Branch A, 2026-07-18 — see `DECISIONS.md`).** Real ETA submission, replaces the simulated `eta_adapter.py` stub. Credentials/sandbox → real submission adapter → signing → status reconcile → archiving+acceptance. **STOP-gate: needs real ETA production/sandbox credentials + the customer's tax profile before FILE_01 there can start** — cannot proceed solo. Index: `FILE_00_INDEX.md` |
| **8D** | `Docs/plan/post-handover-v1_1/` | FILE_01 → FILE_05 **done** (+P2 06–09 not started) | **"The rest" — QA-audit Phase 1/2 (added 2026-07-18).** Phase 1 (FILE_01–05) all done 2026-07-19 — ran ahead of the "after handover" note since none is customer-facing (see `FILE_00_INDEX.md` change log + `DECISIONS.md`). FILE_01 ruff/mypy/bandit CI lint job (baselined ~1679 ruff + 202 mypy + 3494 bandit findings), FILE_02 dep lockfile (`pip-compile`) + Dependabot, FILE_03 backend coverage baseline (89%, floor 84%), FILE_04 frontend Vitest unit tests (money/customFields/workflow, 39 passing), FILE_05 README cross-platform + Django6 deprecation fix. Phase 2 (Nice-to-Have, not started): a11y CI, OpenAPI, arch diagrams, load test. **References-not-duplicates** smart-import UI (pos 10), admin panel/AI-cost (pos 9 FILE_19/20), AI reliability (pos 12). Index: `FILE_00_INDEX.md` |
| **9** | `Docs/plan/twenty-harvest-plan/` | FILE_01 → FILE_21 | **Twenty harvest (added 2026-07-16)** — 20 improvements from the Twenty CRM comparison, tiered: Tier 1 FILE_01–07 ship-safety (versioning, upgrade command+gates, Playwright E2E, webhooks, saved views), Tier 2 FILE_08–13 world-class feel (⌘K actions, approval + AI workflow nodes, custom fields, timeline), Tier 3 FILE_14–20 polish. **FILE_01–03 execute early as part of pos 8's pre-handover set** (done); FILE_04/05/06/07/08/09/11 also done out of numbered order (2026-07-16/18) — FILE_06/07 (saved views) found already built (`erp/identity`), FILE_06 closed as-is, FILE_07 extended to all 22 list pages (sharing/tabs redesign explicitly deferred); FILE_09 (approval node RBAC+audit+notify) built in full, canvas node-card visuals deferred (no node type has custom rendering today — a bigger, separate frontend decision); FILE_10 (assistant-action node + drafts-only save-time validator) done 2026-07-18; FILE_12 (custom fields UI — settings CRUD, dynamic form rendering, table columns, detail facts) done 2026-07-18, built by Agent B on a founder-authorized one-off cross into apps/web territory (see PARALLEL_PLAN.md A7). Next unstarted: FILE_13. Founder may pause at any tier boundary |
| **10** | `Docs/plan/smart-import-plan/` | FILE_01 → FILE_17 | **Phase A** — Smart Import Engine: zero-prep Excel migration (detect, map, clean, dedupe, auto-masters, validate, import, rollback) |
| **11** | `Docs/plan/arp-roadmap.md` | phases A2, B, B2, C–F | The strategic roadmap — only after 1–10 are fully `_done` |
| **12** | `Docs/plan/ai-reliability-roadmap/` | FILE_03 → FILE_08 | **AI engineering long track** (Phases 3–8: retrieval v2, memory, agent orchestration v2, guardrails/security, perf/cost, production hardening). May interleave with pos 11 arp phases at merge checkpoints — founder paces it |
| ~~**★**~~ ✅ | `Docs/plan/agent-actions-plan/` | FILE_01 → FILE_06 **DONE (2026-07-09)** | **Linear-agent "make it DO more" track — CLOSED.** Widened the assistant write surface from 3 actions to 17 (sales/purchasing/inventory/accounting/CRM draft actions), reusing the existing propose→confirm→execute pattern. Acceptance (FILE_06) passed; posting-actions question decided **Option A — stay drafts-only for v1** (recorded in `DECISIONS.md` "Agent actions — drafts-only standing decision reaffirmed"). Option B (posting actions) is not queued anywhere — would need a founder re-open. |
| ~~**PA**~~ ✅ | `Docs/plan/agent-posting-plan/` | FILE_01 → FILE_08 **DONE (2026-07-20)** | **Posting actions — Option B reopened, scoped down — CLOSED.** Shipped without waiting for ai-reliability FILE_05 (unbuilt) — manual guards instead (org-wide `OrgPreferences.assistant_posting_enabled` toggle + reused per-action role checks + typed retype-confirm on `risk="post"` actions). 6 new actions delivered as designed: post a drafted journal entry (new `post_draft_journal_entry()` domain service + manual "Post" button, not assistant-only), receive/bill/pay a purchase order, approve a purchase request, issue stock. Registry now 23 (17 draft + 6 post). Acceptance (FILE_08): 805 backend tests + i18n/tsc/gate03 green; full 8-point matrix automated incl. toggle-off + retype-mismatch. **Benchmark wiring deferred** — FILE_05 bench suite unbuilt; TODO recorded in `FILE_08_ACCEPTANCE_done.md`. Human-only remainder: live browser + dark-mode eyes pass (does not block closing). All work landed on main (no feature branch). Standing v1 tradeoff: no AI number cross-check before a post card — see `DECISIONS.md` close-out. |
| **⟳** | `Docs/testing/E2E_MASTER_PROMPT.md` | single file, self-maintaining | **Standing ops, NOT a queue position (created 2026-07-09)** — master daily E2E regression prompt: an agent drives the real UI through every business journey (4-layer verification: UI/network/backend/business rule), fixes failures, re-verifies, deploys to the docker dev env, reports to `Docs/testing/e2e-reports/`. Runs daily unattended (`/schedule` or Task Scheduler). Its Phase 4 auto-adds journeys for newly shipped features — plan sessions don't need to update it. |
| **⧉** | `C:\AhmedGaid\Modeer\Docs\plan\` (external repo) | 00 → 21 (design done 2026-07-13) | **Modeer — separate product, NOT an ERP queue position.** AI-native multi-project management platform (portfolio dashboard, AI-maintained project brains, prompt launcher). Plan complete; build entry = its `14-mvp.md` Task 0.1. Founder paces it between ERP positions; ERP queue always wins scheduled sessions. |
| ~~**13**~~ ✅ | `Docs/plan/field-primitives-rollout/` | FILE_01 **DONE (2026-07-17)** | **Field primitives rollout** — fanned the two Twenty-harvested primitives (`ComboBox` searchable-select, `DatePicker` calendar) across the app: every long/dynamic entry `<select>` → ComboBox, every `<input type="date">` → DatePicker (~30 selects + ~18 date inputs, all modules). Deferred by design: report-page "All"-default filter selects + select-as-action controls (noted in FILE_01). Founder standing OK covers these UI/UX upgrades. |
| **H** | Dynamic-help Live-checklist rollout (no plan folder — tracked here + commit history) | 18/77 guides done | **Founder-approved, off critical path (2026-07-17).** Roll the Live-tab checklist pattern (alerts + step-by-step hand-holding, see `apps/web/src/help/HelpSignalsContext.tsx` + `HelpCenter.tsx`) to the remaining 59 help guides in `apps/web/src/help/content/*.ts`, batch by batch (~3 pages/batch: read page state → design signals → write guide → wire `useSetHelpSignals` → gates → live-verify → commit). Done so far: Webhooks, New Order, New PO, Journal Entry, Users invite, Leads, Items, New Quotation, Tickets, New Purchase Request, Suppliers, Customers, CRM Campaigns, CRM Pipeline, Price Lists, **Inventory Stock Counts, Inventory Movements, Settings Branches (2026-07-19, A — live-verified, i18n+tsc green)**. Candidates next: Settings Organization, remaining Sales/Purchasing/Accounting detail pages. Pause/resume freely between queue positions — does not block pos 8 handover. |
| **BR** | `Docs/plan/brand-philosophy-review/` | Sessions A → H | **Brand Philosophy Review (added 2026-07-18, off critical path, founder-standing-OK).** Judgment audit of the ENTIRE app (~85 screens, 8 surfaces) against the Product Philosophy front door + the 8 Conductor Standard — drive each screen (ar+en, light+dark), score, file ranked findings. NOT a redesign; fixes are separate sessions. Does NOT block handover — feeds v1.1 polish. **Tonight deliverable = the `brand-review-scorecard` artifact** (rubric + full inventory + known systemic findings). Index: `FILE_00_INDEX.md` |
| **PP** | `Docs/plan/perf-ux-polish/` | FILE_01 → FILE_17 | **Performance & UX Polish (added 2026-07-20, off critical path).** Fix all 121 brand-philosophy-review findings (32 P1 + 57 P2 + 32 P3). Phase 1 (FILE_01–09): P1 fixes breaking trust/transparency. Phase 2 (FILE_10–14): P2 systemic off-brand issues. Phase 3 (FILE_15–17): P3 polish. Founder-paced, run in parallel with queue positions or scheduled later. Index: `FILE_00_INDEX.md` |
| **R** | `Docs/plan/master-roadmap/` | FILE_00 → FILE_13 | **The reservoir (created 2026-07-08)** — 13-domain engineering blueprint, task-level. NOT a queue position: its D4.P1 + D5.P1 + D6.P1 floor tasks slot into natural gaps between queue positions (founder paces); everything else is promoted here into a numbered position when its entry gate opens. Owner mirror: `Docs/OWNER_MANUAL.html` |
| ~~**P**~~ ✅ | `Docs/plan/craft-trust-polish/` | FILE_01 → FILE_03 **DONE (2026-07-19)** | **Craft & Trust polish (added 2026-07-18, off critical path, founder-standing-OK).** Three on-brand adds folded from the CPO "Master Plan" review — all shipped: FILE_01 System Confidence panel (`/api/dashboard/confidence/`), FILE_02 calm milestone moments (`/api/dashboard/milestones/`, company-wide dismiss, no confetti/sound), FILE_03 English product-vocabulary canon (Identity System §6.4 — 9 concepts registered, one drift fixed: "AI ops" → "Assistant health" in both languages). Rejected/guarded items (sounds, silent autosave, column-resize, NL→SQL) are recorded in DECISIONS.md — do not re-queue. |

Why this order: FILE_10 is half-built (uncommitted) — never leave work in flight. RAG next
because rag FILE_10 builds ON safe actions and linear-polish FILE_08/11/12 build on things RAG
doesn't touch. Polish third so ai-workspace FILE_12–14 (detours, import) land on an app that
already has undo/keyboard/views — and FILE_15 acceptance then covers EVERYTHING at once.

## Finding the next task (deterministic — never guess)

1. Recall the `erp-status` skill. If it names a blocker → resolve that first.
2. Take the LOWEST queue position whose plan still has a file WITHOUT the `_done` suffix.
3. Inside that plan: next file = the lowest-numbered `FILE_NN_*.md` without `_done`.
4. That one file is this session's entire scope. Nothing else.

A `_done` file is NEVER reopened. Fixes to shipped work happen in the current session against
the code. The plan folders themselves are the progress bar — no separate tracker.

## Session protocol (every session, no exceptions)

1. **Load:** the plan's `FILE_00_INDEX.md` + the target `FILE_NN`. Nothing more up front.
2. **Model check:** if the file (or the index's Model column) says Sonnet/Haiku fits, say so
   in ONE line and wait for the user to `/model` before burning Opus on mechanical work.
3. **Read before write:** do the file's "Before You Start" reads literally.
4. **Do the tasks. Run the smoke test.** Every box, honestly — a skipped box is a failed box.
5. **Gates:** `apps/web`: `node scripts/check-i18n-parity.mjs` + `npx tsc --noEmit`;
   repo root: `python scripts/gates/gate03.py`; backend sessions: `pytest erp/<app>`.
   UI sessions additionally run the `conductor-brand` brand-feel checklist.
6. **Commit** (conventional message, reference the plan session).
7. **Rename** the file with `_done` appended. Same commit or the next — never forgotten.
8. **Update the `erp-status` skill**: current position + exact NEXT file + any blocker.
9. **Tell the user:** report with a "How to test" block, then instruct — clear this session,
   start fresh for the next file. **One file = one session. Never roll into the next file.**

## Merge checkpoints (branch → main)

Work each plan on a feature branch (`feat/rag-knowledge`, `feat/linear-polish`, …). Merge to
main at the checkpoints the plans define:

- ai-workspace: after FILE_10; after FILE_15
- rag-knowledge: after FILE_05 (backend+prompts), after FILE_07 (UI), after FILE_11 (harness+acceptance)
- linear-polish: after FILE_02, 04, 08, 10 (tier ends), after FILE_13
- unified-ui: after FILE_04 (header bar app-wide), FILE_06 (tables unified), FILE_09 (meta + acceptance)
- smart-import: after FILE_04 (parsing core), FILE_10 (backend engine), FILE_14 (masters
  end-to-end in UI — the Phase A demo point), FILE_17 (documents + finance + acceptance)
- twenty-harvest: after FILE_07 (Tier 1 — the handover-safety merge), FILE_13 (Tier 2),
  FILE_21 (Tier 3 + acceptance)

At every merge: full gate run green FIRST (`gate:all` if time allows at plan ends), then merge,
then update `erp-status`.

## Interrupts and blockers

- **User asks for something outside the queue** (bug, hotfix, question): do it, finish it,
  update `erp-status`, then the queue resumes where it was. The queue yields to the user,
  always.
- **A session's task is blocked** (missing decision, broken dependency, failing unrelated
  test): record the blocker in `erp-status` with the exact question/next step, stop the
  session cleanly. Do NOT skip ahead to a later file in the same plan; DO offer the user the
  next file of the NEXT plan in the queue if the blocker only freezes one plan.
- **Two plans conflict on a file** (should be rare — affected-files lists barely overlap; the
  known touchpoints are `agent.py`, `context.py`, locales): the earlier-queued plan wins;
  the later session rebases on main and adapts.
- **A plan file contradicts the live code** (code moved on since planning): the code + the
  plan file's INTENT win over its literal snippet — adapt the snippet, note the drift in the
  commit message, never blindly paste.

## Standing decisions (do not re-litigate mid-queue)

- Ordering decisions, scope cuts, category rules → `Docs/ARP_STRATEGY.md` wins.
- Tool-use, never free-text-to-SQL. Writes are human-in-the-loop. AI runs as the user.
- Zero new dependencies without asking. Tokens/logical-CSS/parity/monochrome are build-blocking.
- One decision is deliberately OPEN and flagged where it's needed: digits policy
  (linear-polish FILE_09 confirms with the user before enforcing).

## When the queue is empty

All four plans fully `_done` → run nothing new. Update `erp-status`, tell the user the
workspace + polish programs are complete, and point at `Docs/plan/arp-roadmap.md` phase
gating (strategy doc decides what Phase comes next — that's a planning conversation with the
user, not an automatic continuation).

*Maintained by hand. If a new plan folder is added, insert it into the queue table here in the
same commit that creates it.*
