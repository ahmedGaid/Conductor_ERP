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
| **8** | `Docs/plan/twenty-harvest-plan/` | FILE_01 → FILE_21 | **Twenty harvest (added 2026-07-16)** — 20 improvements from the Twenty CRM comparison, tiered: Tier 1 FILE_01–07 ship-safety (versioning, upgrade command+gates, Playwright E2E, webhooks, saved views — protects the live customer, serves the delivery goal), Tier 2 FILE_08–13 world-class feel (⌘K actions, approval + AI workflow nodes, custom fields, timeline), Tier 3 FILE_14–20 polish. Placed ahead of smart-import because smart-import was explicitly deferred as a non-blocker (2026-07-16 decision) while Tier 1 IS handover safety. Founder may pause at any tier boundary and let 9+ resume |
| **9** | `Docs/plan/smart-import-plan/` | FILE_01 → FILE_17 | **Phase A** — Smart Import Engine: zero-prep Excel migration (detect, map, clean, dedupe, auto-masters, validate, import, rollback) |
| **10** | `Docs/plan/arp-roadmap.md` | phases A2, B, B2, C–F | The strategic roadmap — only after 1–9 are fully `_done` |
| **11** | `Docs/plan/ai-reliability-roadmap/` | FILE_03 → FILE_08 | **AI engineering long track** (Phases 3–8: retrieval v2, memory, agent orchestration v2, guardrails/security, perf/cost, production hardening). May interleave with pos 10 arp phases at merge checkpoints — founder paces it |
| **★** | `Docs/plan/agent-actions-plan/` | FILE_01 → FILE_06 | **Founder-prioritized (2026-07-09) — the Linear-agent "make it DO more" track.** Widens the assistant write surface from 3 actions to full per-module draft actions (sales/purchasing/inventory/accounting/CRM), reusing the existing propose→confirm→execute pattern. Drafts-only (no posting) — posting actions are a deferred decision in its FILE_06. NOT machinery: the loop/durability/validation live in ai-reliability FILE_05. Founder may pull this to NEXT ahead of the numbered queue; only file overlap is `actions.py` (earlier session wins, later rebases). |
| **⟳** | `Docs/testing/E2E_MASTER_PROMPT.md` | single file, self-maintaining | **Standing ops, NOT a queue position (created 2026-07-09)** — master daily E2E regression prompt: an agent drives the real UI through every business journey (4-layer verification: UI/network/backend/business rule), fixes failures, re-verifies, deploys to the docker dev env, reports to `Docs/testing/e2e-reports/`. Runs daily unattended (`/schedule` or Task Scheduler). Its Phase 4 auto-adds journeys for newly shipped features — plan sessions don't need to update it. |
| **⧉** | `C:\AhmedGaid\Modeer\Docs\plan\` (external repo) | 00 → 21 (design done 2026-07-13) | **Modeer — separate product, NOT an ERP queue position.** AI-native multi-project management platform (portfolio dashboard, AI-maintained project brains, prompt launcher). Plan complete; build entry = its `14-mvp.md` Task 0.1. Founder paces it between ERP positions; ERP queue always wins scheduled sessions. |
| **R** | `Docs/plan/master-roadmap/` | FILE_00 → FILE_13 | **The reservoir (created 2026-07-08)** — 13-domain engineering blueprint, task-level. NOT a queue position: its D4.P1 + D5.P1 + D6.P1 floor tasks slot into natural gaps between queue positions (founder paces); everything else is promoted here into a numbered position when its entry gate opens. Owner mirror: `Docs/OWNER_MANUAL.html` |

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
