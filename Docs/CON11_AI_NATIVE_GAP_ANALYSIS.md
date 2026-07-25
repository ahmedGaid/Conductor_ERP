# CON-11 — AI-Native ERP (Context → Intent → Action): Current State → Future State Gap Analysis

> Linear CON-11. Decision on the issue: **Later / Not Now for broad implementation** — this file is
> the required first deliverable ("run the architectural and product investigation... do not
> commit to a large implementation roadmap until the gap analysis is complete"). It answers the
> issue's six Next-Step questions against the actual codebase, not against the proposal text.
> Companion to [`ARP_STRATEGY.md`](ARP_STRATEGY.md) and [`ARP_DEEP_VISION.md`](ARP_DEEP_VISION.md) —
> read those first; this file does not repeat their content, it verifies how much of it is real.
> Produced 2026-07-25.

---

## 0. Headline finding

**CON-11 is not a new direction — it is already the adopted direction, and roughly 60–70% of its
own conceptual pipeline is already built or actively in flight.** `ARP_STRATEGY.md` (2026-07-02)
and `ARP_DEEP_VISION.md` (2026-07-07) already reframe Conductor exactly as CON-11 describes:
Context → Intent → Understanding → Plan → Simulation → Human Judgment → Agentic Execution →
Learning maps almost 1:1 onto the deep-vision seven-layer Agentic OS (L0 Action Graph → L1
Verifier → L2 Simulation → L3 Planner/Playbooks → L4 Company Brain → L5 Autonomy Ladder → L6 Agent
Runtime). The gap is not conceptual — it's that L0–L2 are **built and running**, while L3–L6 are
**designed on paper, not started in code**. CON-11's real contribution is a second, independent
validation of the same bet, plus a sharper name for the surface convergence question (assistant +
Inbox + Smart Import + Global Search + ⌘K + record context → one Intent/Action Surface), which
*is* a genuinely open question the existing docs don't fully answer (§5 below).

Recommendation in one line: **do not open a new roadmap track for CON-11.** Fold its language into
`ARP_STRATEGY.md`/`ARP_DEEP_VISION.md` as corroboration (optional, low-cost), and let the existing
queue (`EXECUTION_ORDER.md`) keep producing L3–L6 in the order already decided — Phase A (Smart
Import, in flight) → A2 (Consultant) → B (month-close) → B2 (Company Brain + Autonomy Ladder) → C
(Agent Runtime). The one concrete slice worth pulling forward is in §6.

---

## 1. Mapping CON-11's pipeline onto what exists

| CON-11 stage | Deep-vision layer | Current state | Evidence |
|---|---|---|---|
| **Context** | L4 Company Brain (partial) + ad-hoc context | **Partially built.** Per-request page context exists; per-tenant durable memory does not. | `apps/web/src/assistant/context.ts` (`PageContext`: path, module, current record, recent pages, filters, dirty-form flag, language); RAG document search `erp/assistant/services/knowledge.py`; live entity search backs ⌘K. No alias table, no correction log, no policy memory. |
| **Intent** | Router / tool-use | **Built.** | `erp/assistant/tools.py` (`TOOLS` registry, read-only, actor-scoped, cited); chat/ask endpoints; ⌘K "ask AI" fallthrough (`apps/web/src/app/CommandPalette.tsx`). |
| **Understanding** | Slot-filling + grounding | **Built, per-turn only.** | Agent loop resolves query→record, tool selection, forced grounding before document-shaped answers (deep vision G2, `agent.py`). No persistent company vocabulary (G4's alias resolution is deterministic normalization, not learned aliasing yet). |
| **Plan** | L0 Action Graph + L3 Planner | **L0 built; L3 not started.** | `erp/assistant/services/actions.py` — every `Action` declares `requires`/`effects`/`invariants`/`compensation`/`risk`/`idempotency`, validated at import time (`_validate_action`, line ~1953). 23 registered actions (17 draft + 6 post). **No planner walks the dependency graph from a natural-language goal** — every plan today is either one action or a caller-supplied step list (`workflow` nodes, UI-built lists); "set up my company" style multi-step synthesis does not exist. |
| **Simulation** | L2 | **Built.** | `erp/assistant/services/simulation.py::simulate()` — runs a real step list inside a transaction that always rolls back, returns a diff (`creates`, GL delta, stock delta, receivables/payables delta), runs each action's declared verifier pack. `SimulationDiffCard.tsx` renders it. |
| **Human Judgment** | Propose→confirm (fixed level 1) | **Built; ladder not started.** | Every write is propose→confirm today (agent-posting-plan DONE 2026-07-20: retype-confirm on `risk="post"`). L5 Autonomy Ladder (levels 0–4, earned promotion) is designed (`ARP_DEEP_VISION.md` §2 L5) but has zero code — there is no per-(user,action) trust level anywhere in the models. |
| **Agentic Execution** | Execution through module contracts | **Built.** | `actions.execute()` runs as the actor through the same service layer as a human click; RBAC + audit hold by construction (`erp/audit/services.py::record`, called from every action). No direct ORM writes from AI, no free-text-to-SQL — verified in code, not just asserted in docs. |
| **Business Outcome** | Module system of record | **Built** (this is the ERP itself — sales/purchasing/inventory/accounting modules, unchanged by the AI layer). | n/a |
| **Learning** | L4 correction log + L1 verifier history + L6 agent runtime | **Not started.** | No correction-log table, no per-tenant pattern memory, no background agent roster, no scheduler. The "eval harness" (`erp/assistant/evals/`) that would let *the team* learn is planned at `ai-reliability-roadmap` (queue pos 6/12) but is about model/prompt quality, not company-level learning. |

**Read straight off this table:** the "kernel" (L0–L2 — deterministic plan skeleton, dry-run
simulation, verified execution) is real and tested. The "OS" (L3–L6 — planning from intent,
per-tenant memory, graduated autonomy, background agents) is the part CON-11 is actually asking
about, and it is genuinely all still ahead of us. That is a faithful, non-hand-wavy answer to "what
already exists / what is missing."

---

## 2. RBAC, service contracts, audit — the trust substrate CON-11 assumes

CON-11's description insists the AI "must never bypass RBAC, service contracts, validation,
business rules, audit logging, approval policies" and "no direct ORM writes, no free-text-to-SQL."
This is **already a load-bearing, enforced property of the codebase**, not an aspiration:

- Every `Action.execute` call runs through the normal module service function as the current actor
  — same function a human-driven view calls (`erp/assistant/services/actions.py::execute`).
- Granular RBAC (`erp/identity/roles_admin.py`, `rbac.py`) — modules × entities × actions × scope,
  enforced by the same permission checks the AI's actions call into.
- Every state-changing action calls `erp.audit.services.record(...)` (traced through
  `roles_admin.py`, `actions.py`, `simulation.py`, workflow's `assistant_action.py` executor, etc.)
  — one audit trail for human and AI actions alike.
- `_validate_action` is an **import-time assertion**, not a runtime hope: a posting/stock-moving
  effect *cannot* declare `risk` below `"post"`, and any invariant name that isn't a registered
  verifier pack fails module load. Misconfiguration is a deploy-time crash, not a live bug.
- Destructive kinds (`delete`, `cancel`, `approve`, `post`, `reverse`, `close_period`, `bulk`,
  `adjust`) can never ship with `requires_confirm=False` — also asserted at import time.

Conclusion: the "trusted business capabilities" CON-11 wants the AI to execute through are not a
future integration point — they are the substrate the AI layer was built on top of from the start
(`ARP_STRATEGY.md` §3, mechanic 1). This significantly de-risks any future L3–L6 work: the planner
and autonomy ladder only need to sit *on top of* this, never punch through it.

---

## 3. The Intent/Action Surface convergence question (CON-11's genuinely open question)

CON-11 asks: *"How can the current AI Assistant, Inbox, Smart Import, Global Search, Command
Palette, and Current Record Context converge into a coherent Intent/Action Surface?"* This is the
one question in the issue that the existing strategy docs don't already answer, because it's a UX
architecture question, not an AI architecture question.

Current state of each surface:

- **Command Palette** (`apps/web/src/app/CommandPalette.tsx`) is already the most converged
  surface: static "go to" commands, page-registered contextual actions, live entity search
  (server-backed, ar/en tolerant), and an "ask AI" fallthrough row that opens the assistant panel
  pre-filled with the typed question — all in one ranked, keyboard-driven list. This is deep
  vision's **G5 (three roads to everything)** already working for search+navigate+ask.
- **AI Assistant panel** carries its own chat/ask surface, proposal cards, simulation preview, and
  page-context awareness (`PageContext`) — but it is a separate panel, not merged into the palette
  beyond the fallthrough row.
- **Global Search** (the palette's live "results" group) is entity search only — it does not (yet)
  search actions, playbooks, or past agent runs.
- **Inbox** (`erp/notifications/services/inbox.py`, `NotificationsPage.tsx`) is a human-facing
  notification feed today (approvals, digests) — it is not yet the "agent inbox" deep vision
  describes for L6 (evidence-linked findings with one-tap simulated fixes), because L6 doesn't
  exist yet.
- **Smart Import** has its own wizard UI, separate from chat and palette, though `ai-workspace`
  session 14's "assistant import card" already lets the chat surface delegate into it.
- **Current Record Context** (`PageContext.record`) already travels into every chat/ask call and
  every command-palette open — the unification point already exists structurally; it's the four
  surfaces around it that are still separate UIs.

**Gap:** there is no single registry today that says "this capability is reachable from the
palette, the chat, and a nav item, with one registration" — G5 works by convention (each surface
happens to read the same tool/action catalogs), not by a shared "Intent Surface" abstraction. That
abstraction is exactly what deep vision's L0 registry decorator is *starting* to provide for
actions (one decorator → agent-operable + registered), but it does not yet extend to search,
Inbox, or Import. Formalizing it is a real, scoped, mid-size frontend/architecture task — a
reasonable candidate for a future plan file, **not urgent, not blocking anything today.**

---

## 4. What a formal "Business Context Layer" would need that doesn't exist yet

CON-11 lists: current user/company/page/record (exists in `PageContext`) — relationships, customer
history, supplier history, inventory state, financial state, business policies, permissions
(exists via RBAC/report tools), previous decisions, relevant documents (RAG covers this),
conversations, workflows, recent events, business objectives.

Everything past "page/record/permissions" is **queryable through existing read tools and reports,
but not pre-assembled into one context object** — an agent (or a human) can ask for "this
customer's history" and get a real, cited answer via a tool call, but there is no standing
`BusinessContext` record that a planner could consult without a live query. This is precisely what
`ARP_DEEP_VISION.md` L4 (Company Brain) is designed to become — alias table, correction log,
policy memory, pattern memory — and it is correctly scheduled at **Phase B2, after the month-close
flagship (Phase B)**, on the stated reasoning that it needs real usage data to learn from. That
reasoning holds: building a "Business Context Layer" before there are real corrections and policies
to populate it would produce an empty, unvalidated schema.

**Conclusion: no, we do not need a *new* Business Context Layer initiative.** Phase B2 already is
that initiative, correctly sequenced. CON-11 doesn't change its scope or its position in the queue.

---

## 5. Answering the issue's six questions directly

**1. Should Conductor pursue this direction?**
Yes — moot in the sense that it already has been (`ARP_STRATEGY.md`, adopted 2026-07-02;
`ARP_DEEP_VISION.md`, adopted 2026-07-07, founder-approved). CON-11 is confirmation, not a new
decision. No reversal is warranted by anything found in this investigation.

**2. What already exists?**
L0 Action Graph (declared requires/effects/invariants/compensation/risk/idempotency, 23 actions),
L1 Verifier (invariant packs run after every write, auto-fail-and-report), L2 Simulation (real
dry-run in a rolled-back transaction, diff card), the RBAC/audit/service-contract substrate all of
it rides on, a RAG knowledge base, a mature ⌘K/search/ask three-roads surface, and 6 post-risk
actions with retype-confirm. See §1.

**3. What is missing?**
L3 Planner (multi-step synthesis from a goal, playbooks/SOPs), L4 Company Brain (alias table,
correction log, policy memory, pattern memory), L5 Autonomy Ladder (earned trust levels), L6 Agent
Runtime (scheduler, agent charters, agent inbox, the actual background roster — Bookkeeper,
Auditor, Stock Controller, Collector, Cash Forecaster, Compliance, Coach, Data Janitor). Also
missing: a unifying Intent-Surface registry across palette/chat/Inbox/search/import (§3) and a
standing eval harness for agent quality (queued at `ai-reliability-roadmap`, not yet built).

**4. What can be reused?**
Everything in §1's "built" rows is reusable as-is: the Action Graph is designed so that a future
planner *walks* it rather than replacing it; the simulation engine already accepts an arbitrary
step list, so a planner only needs to *produce* that list, not change how it's dry-run; the
verifier and audit trail need zero changes to serve L3–L6. This is the payoff of building L0–L2
first, as the roadmap already chose to.

**5. Smallest viable AI-native Conductor v1?**
It's already defined and mostly built: **Phase W+ (done) → Phase A Smart Import (in flight,
queue position 10) → Phase A2 Implementation Consultant → Phase B month-close (the flagship,
public-claims-gate trigger)**. That sequence — not a new one — is the smallest viable path to a
demonstrable "Context → Intent → Plan → Simulate → Approve → Execute" loop a customer can watch
end-to-end. B2 (Company Brain/Autonomy) and C (Agent Runtime) are correctly *after* v1, since they
need v1's usage data to be worth building.

**6. ONE concrete first implementation slice?**
Not a new one — see §6. If the founder wants a CON-11-flavored artifact independent of the queue,
the only genuinely new, small, low-risk slice this investigation surfaced is the Intent-Surface
registry scoping pass in §3 (a `FILE_00` scoping session, not a build) — everything else CON-11
asks for is already the next thing in `EXECUTION_ORDER.md`.

---

## 6. Recommendation

- **Do not create a new roadmap track, plan folder, or queue position for CON-11.** It validates
  the existing one. Creating a parallel track would violate the "one source of truth" rule already
  applied once before to the CPO Master Plan review (`arp-roadmap.md` §"Craft & Trust polish").
- **Keep CON-11 open on Linear as "Later/Not Now — investigation complete, direction confirmed,"**
  linking this file, so the questions don't get re-asked from scratch in six months.
- **Optional, cheap, not urgent:** fold one line into `ARP_DEEP_VISION.md`'s change log noting
  CON-11 as a second, independently-derived validation of the L0–L6 model (§10-style entry) —
  purely a provenance note, no scope change.
- **The one real to-do this investigation found:** file a `FILE_00` scoping stub for the
  Intent-Surface registry question (§3) into the `R` reservoir (`Docs/plan/master-roadmap/`) or as
  a stub under `arp-roadmap.md`'s "Craft & Trust polish" section, the same way the attachments/
  photo-avatars/smart-import-entry-point stubs were filed — **not built now**, just not lost.
- **Next actual build work stays exactly where `EXECUTION_ORDER.md` already has it:** finish Smart
  Import (queue position 10), then A2, then B. No change of course.

## 7. Confidence & method notes

- All "built" claims in §1–§2 are verified against on-disk source (CodeGraph-indexed, re-read live
  for this file: `erp/assistant/services/actions.py`, `simulation.py`, `knowledge.py`,
  `erp/identity/roles_admin.py`, `apps/web/src/app/CommandPalette.tsx`,
  `apps/web/src/assistant/context.ts`), not recalled from memory or taken from planning-doc claims
  alone.
- "Missing" claims (L3–L6) are verified by absence: no `codegraph_explore` query for planner /
  playbook / autonomy / trust-level / agent-charter / scheduler symbols returned any matching
  production code — only the design language in `ARP_DEEP_VISION.md` and forward references in the
  roadmap ("when reached: `Docs/plan/brain-autonomy-plan/`" etc., none of which exist yet).
  Absence-of-evidence was cross-checked by re-querying with adjacent terms before concluding.
- The original Linear issue's "AI Agent Prompt" field was empty (placeholder text only); per the
  founder, the issue description itself is the intended brief — this file was produced against
  that brief, not a separate document.
